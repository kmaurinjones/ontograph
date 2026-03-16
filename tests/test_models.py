"""Tests for domain models."""

import json

from ontograph.models import Alias, Entity, OrbitEntry, Relationship, Schema


def test_entity_roundtrip():
    e = Entity(name="Lena", entity_type="person", attributes={"role": "engineer"})
    row = e.to_row()
    assert row["name"] == "Lena"
    assert row["entity_type"] == "person"
    assert json.loads(row["attributes"])["role"] == "engineer"

    restored = Entity.from_row(row)
    assert restored.name == e.name
    assert restored.entity_type == e.entity_type
    assert restored.attributes["role"] == "engineer"
    assert restored.id == e.id


def test_entity_file_refs_roundtrip():
    e = Entity(
        name="receipt", entity_type="document",
        file_refs=["/Users/me/receipts/laptop.pdf", "/Users/me/photos/laptop.jpg"],
    )
    row = e.to_row()
    restored = Entity.from_row(row)
    assert restored.file_refs == ["/Users/me/receipts/laptop.pdf", "/Users/me/photos/laptop.jpg"]
    assert restored.name == "receipt"


def test_entity_empty_file_refs_roundtrip():
    e = Entity(name="plain", entity_type="thing")
    row = e.to_row()
    restored = Entity.from_row(row)
    assert restored.file_refs == []


def test_relationship_roundtrip():
    r = Relationship(
        source_id="abc", target_id="def",
        relationship_type="works_on", directed=True,
        attributes={"since": "2024"},
    )
    row = r.to_row()
    assert row["directed"] == 1
    assert row["relationship_type"] == "works_on"

    restored = Relationship.from_row(row)
    assert restored.directed is True
    assert restored.source_id == "abc"
    assert restored.attributes["since"] == "2024"


def test_relationship_direction_property():
    directed = Relationship(source_id="a", target_id="b", relationship_type="x", directed=True)
    assert directed.direction == "directed"

    bidirectional = Relationship(
        source_id="a", target_id="b", relationship_type="y", directed=False,
    )
    assert bidirectional.direction == "bidirectional"


def test_alias_roundtrip():
    a = Alias(entity_id="abc123", alias="Sal", alias_type="transcript_error")
    row = a.to_row()
    restored = Alias.from_row(row)
    assert restored.alias == "Sal"
    assert restored.alias_type == "transcript_error"
    assert restored.entity_id == "abc123"


def test_schema_roundtrip():
    s = Schema(
        name="workplace",
        entity_types=["person", "project"],
        relationship_types=[
            {"name": "works_on", "directed": True},
            {"name": "colleague", "directed": False},
        ],
    )
    row = s.to_row()
    restored = Schema.from_row(row)
    assert restored.name == "workplace"
    assert "person" in restored.entity_types
    assert restored.relationship_type_names == ["works_on", "colleague"]


def test_orbit_entry_roundtrip():
    o = OrbitEntry(
        observer_id="obs1", entity_id="ent1",
        interaction_count=5, proximity_score=0.85,
        last_interaction="2026-03-15T12:00:00+00:00",
    )
    row = o.to_row()
    restored = OrbitEntry.from_row(row)
    assert restored.interaction_count == 5
    assert restored.proximity_score == 0.85
    assert restored.observer_id == "obs1"
