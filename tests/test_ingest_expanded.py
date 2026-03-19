"""Tests for ingest prompt tuning and provenance metadata."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ontograph.db import GraphDB
from ontograph.ingest import EXTRACTION_SYSTEM, _build_extraction_prompt, ingest
from ontograph.models import Schema


@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        g = GraphDB(path)
        yield g
        g.close()


# ── Prompt content tests ──


def test_extraction_system_mentions_decisions():
    """System prompt should mention decisions as an extraction target."""
    assert "decision" in EXTRACTION_SYSTEM.lower()


def test_extraction_system_mentions_goals():
    """System prompt should mention goals as an extraction target."""
    assert "goal" in EXTRACTION_SYSTEM.lower()


def test_extraction_system_mentions_insights():
    """System prompt should mention insights as an extraction target."""
    assert "insight" in EXTRACTION_SYSTEM.lower()


def test_extraction_system_mentions_sessions():
    """System prompt should mention sessions as an extraction target."""
    assert "session" in EXTRACTION_SYSTEM.lower()


def test_extraction_prompt_requests_enriched_attributes():
    """Prompt should request status, confidence, and temporal attributes."""
    schema = Schema(
        name="test",
        entity_types=["decision", "goal", "insight", "session", "person", "project"],
        relationship_types=[
            {"name": "decided_during", "directed": True},
            {"name": "supports", "directed": True},
        ],
    )
    prompt = _build_extraction_prompt("Some text", schema)
    prompt_lower = prompt.lower()
    assert "status" in prompt_lower
    assert "confidence" in prompt_lower
    assert "temporal" in prompt_lower


def test_extraction_prompt_asks_for_new_entity_types():
    """Prompt should explicitly ask for decisions, goals, insights extraction."""
    prompt = _build_extraction_prompt("Team decided to delay the launch until Q3.", schema=None)
    prompt_lower = prompt.lower()
    assert "decision" in prompt_lower
    assert "goal" in prompt_lower
    assert "insight" in prompt_lower


# ── Provenance metadata tests ──


def _mock_llm_response():
    """Standard mock LLM extraction response."""
    return {
        "entities": [
            {"name": "Launch delay", "type": "decision", "attributes": {"status": "active"}},
            {"name": "Ship MVP", "type": "goal", "attributes": {"status": "active"}},
        ],
        "relationships": [
            {
                "source": "Launch delay",
                "target": "Ship MVP",
                "type": "blocks",
                "directed": True,
                "attributes": {},
            },
        ],
    }


@patch("ontograph.ingest.llm_call_json", return_value=_mock_llm_response())
@patch("ontograph.ingest.embed", return_value=[0.0] * 256)
@patch("ontograph.resolve.embed", return_value=[0.0] * 256)
def test_ingest_with_session_id_stamps_relationships(
    mock_resolve_embed, mock_embed, mock_llm, db,
):
    """When session_id is provided, relationships get source_session_id and extracted_at."""
    ingest(db, "Team decided to delay launch.", session_id="sess-abc123")

    # Find the created relationship
    entities = db.list_entities()
    assert len(entities) >= 2

    # Get relationships for any entity
    for entity in entities:
        rels = db.get_relationships(entity.id)
        for rel in rels:
            assert rel.attributes["source_session_id"] == "sess-abc123"
            assert "extracted_at" in rel.attributes


@patch("ontograph.ingest.llm_call_json", return_value=_mock_llm_response())
@patch("ontograph.ingest.embed", return_value=[0.0] * 256)
@patch("ontograph.resolve.embed", return_value=[0.0] * 256)
def test_ingest_without_session_id_no_session_provenance(
    mock_resolve_embed, mock_embed, mock_llm, db,
):
    """Without session_id, relationships should not have source_session_id."""
    ingest(db, "Team decided to delay launch.")

    entities = db.list_entities()
    for entity in entities:
        rels = db.get_relationships(entity.id)
        for rel in rels:
            assert "source_session_id" not in rel.attributes


@patch("ontograph.ingest.llm_call_json", return_value=_mock_llm_response())
@patch("ontograph.ingest.embed", return_value=[0.0] * 256)
@patch("ontograph.resolve.embed", return_value=[0.0] * 256)
def test_ingest_with_session_id_stamps_entities(
    mock_resolve_embed, mock_embed, mock_llm, db,
):
    """When session_id is provided, entities get source_session_id in attributes."""
    ingest(db, "Team decided to delay launch.", session_id="sess-xyz789")

    entities = db.list_entities()
    for entity in entities:
        assert entity.attributes["source_session_id"] == "sess-xyz789"


@patch("ontograph.ingest.llm_call_json", return_value=_mock_llm_response())
@patch("ontograph.ingest.embed", return_value=[0.0] * 256)
@patch("ontograph.resolve.embed", return_value=[0.0] * 256)
def test_ingest_session_id_in_return_dict(mock_resolve_embed, mock_embed, mock_llm, db):
    """Ingest return dict should include session_id when provided."""
    result = ingest(db, "Team decided to delay launch.", session_id="sess-abc123")
    assert result["session_id"] == "sess-abc123"


@patch("ontograph.ingest.llm_call_json", return_value=_mock_llm_response())
@patch("ontograph.ingest.embed", return_value=[0.0] * 256)
@patch("ontograph.resolve.embed", return_value=[0.0] * 256)
def test_ingest_without_session_id_return_dict(mock_resolve_embed, mock_embed, mock_llm, db):
    """Ingest return dict should have session_id as None when not provided."""
    result = ingest(db, "Team decided to delay launch.")
    assert result["session_id"] is None


@patch("ontograph.ingest.llm_call_json", return_value=_mock_llm_response())
@patch("ontograph.ingest.embed", return_value=[0.0] * 256)
@patch("ontograph.resolve.embed", return_value=[0.0] * 256)
def test_ingest_extracted_at_is_iso_utc(
    mock_resolve_embed, mock_embed, mock_llm, db,
):
    """extracted_at should be a valid ISO UTC timestamp."""
    ingest(db, "Team decided to delay launch.", session_id="sess-ts")

    entities = db.list_entities()
    for entity in entities:
        rels = db.get_relationships(entity.id)
        for rel in rels:
            ts = rel.attributes["extracted_at"]
            # Should parse without error
            parsed = datetime.fromisoformat(ts)
            assert parsed.tzinfo is not None  # must be timezone-aware
