"""Tests for GraphDB (SQLite layer)."""

import tempfile
from pathlib import Path

import pytest

from ontograph.db import GraphDB
from ontograph.models import Alias, Entity, OrbitEntry, Relationship, Schema


@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        g = GraphDB(path)
        yield g
        g.close()


def test_insert_and_get_entity(db: GraphDB):
    e = Entity(name="Lena", entity_type="person")
    db.insert_entity(e)
    got = db.get_entity(e.id)
    assert got is not None
    assert got.name == "Lena"
    assert got.entity_type == "person"


def test_get_entity_by_name(db: GraphDB):
    e = Entity(name="Dev", entity_type="person")
    db.insert_entity(e)
    got = db.get_entity_by_name("dev")  # case-insensitive
    assert got is not None
    assert got.id == e.id


def test_get_entity_by_name_with_type(db: GraphDB):
    e1 = Entity(name="Alpha", entity_type="project")
    e2 = Entity(name="Alpha", entity_type="team")
    db.insert_entity(e1)
    db.insert_entity(e2)

    got = db.get_entity_by_name("Alpha", entity_type="team")
    assert got is not None
    assert got.entity_type == "team"


def test_list_entities(db: GraphDB):
    db.insert_entity(Entity(name="A", entity_type="person"))
    db.insert_entity(Entity(name="B", entity_type="project"))
    db.insert_entity(Entity(name="C", entity_type="person"))

    all_entities = db.list_entities()
    assert len(all_entities) == 3

    people = db.list_entities(entity_type="person")
    assert len(people) == 2


def test_insert_and_get_relationship(db: GraphDB):
    e1 = Entity(name="X", entity_type="person")
    e2 = Entity(name="Y", entity_type="project")
    db.insert_entity(e1)
    db.insert_entity(e2)

    r = Relationship(source_id=e1.id, target_id=e2.id, relationship_type="works_on")
    db.insert_relationship(r)

    rels = db.get_relationships(e1.id)
    assert len(rels) >= 1
    assert rels[0].relationship_type == "works_on"


def test_relationship_exists(db: GraphDB):
    e1 = Entity(name="A", entity_type="person")
    e2 = Entity(name="B", entity_type="person")
    db.insert_entity(e1)
    db.insert_entity(e2)

    assert not db.relationship_exists(e1.id, e2.id, "friend")

    r = Relationship(source_id=e1.id, target_id=e2.id, relationship_type="friend", directed=False)
    db.insert_relationship(r)

    assert db.relationship_exists(e1.id, e2.id, "friend")


def test_alias_insert_and_find(db: GraphDB):
    e = Entity(name="Sam", entity_type="person")
    db.insert_entity(e)

    alias = Alias(entity_id=e.id, alias="Sal", alias_type="transcript_error")
    db.insert_alias(alias)

    found = db.find_entity_by_alias("Sal")
    assert found is not None
    assert found.id == e.id

    aliases = db.get_aliases(e.id)
    assert len(aliases) == 1
    assert aliases[0].alias == "Sal"


def test_orbit_upsert(db: GraphDB):
    e1 = Entity(name="Observer", entity_type="person")
    e2 = Entity(name="Target", entity_type="person")
    db.insert_entity(e1)
    db.insert_entity(e2)

    entry = OrbitEntry(
        observer_id=e1.id, entity_id=e2.id,
        interaction_count=1, proximity_score=0.5,
    )
    db.upsert_orbit(entry)

    got = db.get_orbit_entry(e1.id, e2.id)
    assert got is not None
    assert got.interaction_count == 1

    # Upsert again — count should add
    entry2 = OrbitEntry(
        observer_id=e1.id, entity_id=e2.id,
        interaction_count=1, proximity_score=0.7,
    )
    db.upsert_orbit(entry2)

    got2 = db.get_orbit_entry(e1.id, e2.id)
    assert got2 is not None
    assert got2.interaction_count == 2


def test_schema_crud(db: GraphDB):
    s = Schema(
        name="test_schema",
        entity_types=["person", "project"],
        relationship_types=[{"name": "works_on", "directed": True}],
    )
    db.insert_schema(s)

    got = db.get_schema("test_schema")
    assert got is not None
    assert "person" in got.entity_types

    all_schemas = db.list_schemas()
    assert len(all_schemas) == 1


def test_fts_search(db: GraphDB):
    db.insert_entity(Entity(name="Knowledge Graph Project", entity_type="project"))
    db.insert_entity(Entity(name="Lena Park", entity_type="person"))
    db.insert_entity(Entity(name="Dev Patel", entity_type="person"))

    results = db.search_entities_fts("Lena", limit=5)
    assert len(results) == 1
    assert results[0].name == "Lena Park"

    results2 = db.search_entities_fts("project", limit=5)
    assert len(results2) >= 1


def test_graph_neighbors(db: GraphDB):
    a = Entity(name="A", entity_type="person")
    b = Entity(name="B", entity_type="person")
    c = Entity(name="C", entity_type="person")
    db.insert_entity(a)
    db.insert_entity(b)
    db.insert_entity(c)

    db.insert_relationship(Relationship(source_id=a.id, target_id=b.id, relationship_type="knows"))
    db.insert_relationship(Relationship(source_id=b.id, target_id=c.id, relationship_type="knows"))

    # Depth 1 from A → should find B
    neighbors_1 = db.get_neighbors(a.id, depth=1)
    neighbor_ids = {n.id for n in neighbors_1}
    assert b.id in neighbor_ids
    assert c.id not in neighbor_ids

    # Depth 2 from A → should find B and C
    neighbors_2 = db.get_neighbors(a.id, depth=2)
    neighbor_ids_2 = {n.id for n in neighbors_2}
    assert b.id in neighbor_ids_2
    assert c.id in neighbor_ids_2


def test_stats(db: GraphDB):
    db.insert_entity(Entity(name="X", entity_type="person"))
    s = db.stats()
    assert s["entities"] == 1
    assert s["relationships"] == 0


def test_resolution_log(db: GraphDB):
    db.log_resolution("Sal", None, 0.65)
    accuracy = db.get_resolution_accuracy()
    assert accuracy["total"] == 0  # no reviewed entries yet


def test_entity_file_refs(db: GraphDB):
    e = Entity(
        name="receipt",
        entity_type="document",
        file_refs=["/abs/path/receipt.pdf"],
    )
    db.insert_entity(e)
    got = db.get_entity(e.id)
    assert got is not None
    assert got.file_refs == ["/abs/path/receipt.pdf"]


def test_entity_file_refs_default_empty(db: GraphDB):
    e = Entity(name="plain", entity_type="thing")
    db.insert_entity(e)
    got = db.get_entity(e.id)
    assert got is not None
    assert got.file_refs == []


def test_update_entity_file_refs(db: GraphDB):
    e = Entity(name="doc", entity_type="document")
    db.insert_entity(e)

    db.update_entity_file_refs(e.id, ["/path/a.pdf", "/path/b.png"])
    got = db.get_entity(e.id)
    assert got is not None
    assert got.file_refs == ["/path/a.pdf", "/path/b.png"]
