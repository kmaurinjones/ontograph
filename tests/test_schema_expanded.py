"""Tests for the pre-built expanded schema."""

import tempfile
from pathlib import Path

from ontograph.db import GraphDB
from ontograph.models import Schema
from ontograph.schema_registry import (
    EXPANDED_ENTITY_TYPES,
    EXPANDED_RELATIONSHIP_TYPES,
    EXPANDED_SCHEMA,
)


def test_expanded_schema_is_valid_schema():
    """EXPANDED_SCHEMA must be a valid Schema instance."""
    assert isinstance(EXPANDED_SCHEMA, Schema)
    assert EXPANDED_SCHEMA.name == "expanded"


def test_expanded_entity_types_include_new_types():
    """Must include decision, goal, insight, session entity types."""
    required = {"decision", "goal", "insight", "session"}
    actual = set(EXPANDED_SCHEMA.entity_types)
    assert required.issubset(actual), f"Missing: {required - actual}"


def test_expanded_entity_types_include_standard_types():
    """Must include standard types: person, project, organization, topic, event, location."""
    standard = {"person", "project", "organization", "topic", "event", "location"}
    actual = set(EXPANDED_SCHEMA.entity_types)
    assert standard.issubset(actual), f"Missing: {standard - actual}"


def test_expanded_relationship_types_present():
    """Must include all 7 new directed relationship types."""
    required_names = {
        "decided_during",
        "relates_to",
        "blocks",
        "blocked_by",
        "supports",
        "originated_in",
        "updated_status",
    }
    actual_names = set(EXPANDED_SCHEMA.relationship_type_names)
    assert required_names.issubset(actual_names), f"Missing: {required_names - actual_names}"


def test_new_relationship_types_are_directed():
    """All new relationship types should be directed."""
    rel_map = {r["name"]: r["directed"] for r in EXPANDED_SCHEMA.relationship_types}
    for name in [
        "decided_during",
        "relates_to",
        "blocks",
        "blocked_by",
        "supports",
        "originated_in",
        "updated_status",
    ]:
        assert rel_map[name] is True, f"{name} should be directed"


def test_expanded_schema_registers_in_db():
    """Should be registerable in GraphDB without errors."""
    with tempfile.TemporaryDirectory() as tmp:
        db = GraphDB(Path(tmp) / "test.db")
        db.insert_schema(EXPANDED_SCHEMA)
        got = db.get_schema("expanded")
        assert got is not None
        assert set(got.entity_types) == set(EXPANDED_SCHEMA.entity_types)
        assert set(got.relationship_type_names) == set(EXPANDED_SCHEMA.relationship_type_names)
        db.close()


def test_entity_types_constant_matches_schema():
    """EXPANDED_ENTITY_TYPES list should match what's in the schema."""
    assert set(EXPANDED_ENTITY_TYPES) == set(EXPANDED_SCHEMA.entity_types)


def test_relationship_types_constant_matches_schema():
    """EXPANDED_RELATIONSHIP_TYPES list should match what's in the schema."""
    schema_rel_names = set(EXPANDED_SCHEMA.relationship_type_names)
    constant_names = {r["name"] for r in EXPANDED_RELATIONSHIP_TYPES}
    assert constant_names == schema_rel_names


def test_expanded_schema_roundtrip():
    """Schema should survive to_row/from_row roundtrip."""
    row = EXPANDED_SCHEMA.to_row()
    restored = Schema.from_row(row)
    assert set(restored.entity_types) == set(EXPANDED_SCHEMA.entity_types)
    assert set(restored.relationship_type_names) == set(EXPANDED_SCHEMA.relationship_type_names)
