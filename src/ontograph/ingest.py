"""Ingestion pipeline: unstructured text → entities + relationships.

Takes any unstructured text source — meeting transcript, project brief, notes —
and breaks it into the smallest meaningful units of information, extracting
entities, relationships, and attributes into the knowledge graph.

The LLM handles extraction. The schema constrains what types are valid.
Entity resolution prevents duplicates. Orbit tracking records interactions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from ontograph.db import GraphDB
from ontograph.llm import embed, llm_call_json
from ontograph.models import Document, Relationship, Schema
from ontograph.orbit import bulk_record_interactions
from ontograph.resolve import resolve_or_create

EXTRACTION_SYSTEM = """You are a precise knowledge extraction engine. Extract structured information
from unstructured text. Return ONLY valid JSON, no markdown fences.

You must decompose the text into the smallest meaningful units:
- Entities: people, organizations, projects, topics, locations, events, etc.
- Decisions: any choices made or commitments stated ("decided to X", "chose Y over Z")
- Goals: objectives, targets, milestones ("reach X by Y", "ship Z by date")
- Insights: learned facts, realizations, discoveries ("found that X", "realized Y")
- Sessions: references to meetings, conversations, or work sessions
- Relationships: how entities connect (with direction)
- Attributes: properties of entities mentioned in the text

For each entity, also extract these enriched attributes when present:
- status: "active", "completed", "abandoned", or "paused"
- confidence: 0.0–1.0 indicating how certain the extraction is
- temporal: any time reference ("2026-Q3", "by July 2026", "this week")
- source_project: the project name this entity relates to

Be exhaustive — extract every entity, decision, goal, insight, and relationship.
Be precise — use exact names as they appear in the text.
Be conservative — only extract what is explicitly stated or strongly implied."""


def _build_extraction_prompt(text: str, schema: Schema | None) -> str:
    """Build the LLM prompt for entity/relationship extraction."""
    type_constraint = ""
    if schema:
        type_constraint = f"""
Use ONLY these entity types: {json.dumps(schema.entity_types)}
Use ONLY these relationship types: {json.dumps(schema.relationship_type_names)}
If an entity or relationship doesn't fit these types, use the closest match or skip it.
"""

    return f"""{type_constraint}
Extract all entities and relationships from the following text.
Pay special attention to:
- Any decision made or commitment stated
- Any goal, objective, target, or milestone discussed
- Any insight, learned fact, or realization mentioned
- Which project each entity relates to

For entity attributes, include when present:
- "status": one of "active", "completed", "abandoned", "paused"
- "confidence": 0.0–1.0 (how certain you are about this extraction)
- "temporal": any time reference associated with this entity (e.g. "2026-Q3", "by July 2026")
- "source_project": the project name this entity relates to

Return JSON in this exact format:
{{
    "entities": [
        {{
            "name": "exact name as it appears",
            "type": "entity_type",
            "attributes": {{"key": "value"}}
        }}
    ],
    "relationships": [
        {{
            "source": "source entity name",
            "target": "target entity name",
            "type": "relationship_type",
            "directed": true,
            "attributes": {{"key": "value"}}
        }}
    ]
}}

TEXT:
{text}"""


def _utc_now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def ingest(
    db: GraphDB,
    text: str,
    source_type: str = "text",
    schema_name: str | None = None,
    observer_id: str | None = None,
    metadata: dict | None = None,
    session_id: str | None = None,
) -> dict:
    """Ingest unstructured text into the knowledge graph.

    This is the primary entry point for getting information into the graph.
    It handles the full pipeline:
    1. Store the source document
    2. LLM extracts entities and relationships
    3. Entity resolution prevents duplicates
    4. New entities get embeddings
    5. Relationships are created (with provenance metadata if session_id provided)
    6. Orbit tracking records interactions

    Args:
        db: The graph database
        text: Raw unstructured text to ingest
        source_type: Type of source ('transcript', 'brief', 'note', etc.)
        schema_name: Optional ontology schema to constrain extraction
        observer_id: Entity ID of the observer (for orbit tracking)
        metadata: Optional metadata dict for the source document
        session_id: Optional session ID for provenance tracking. When provided,
            all entities and relationships created during this ingestion are
            stamped with source_session_id and extracted_at.

    Returns:
        Summary dict with counts of entities and relationships created/resolved.
    """
    # 1. Store source document
    doc = Document(
        content=text,
        source_type=source_type,
        metadata=metadata or {},
    )
    doc_embedding = embed(text[:8000])  # embed first 8k chars for searchability
    db.insert_document(doc, embedding=doc_embedding)

    # 2. Get schema if specified
    schema = None
    if schema_name:
        schema = db.get_schema(schema_name)
        if schema is None:
            raise ValueError(f"Schema '{schema_name}' not found. Register it first.")

    # 3. LLM extraction
    prompt = _build_extraction_prompt(text, schema)
    extracted = llm_call_json(prompt, system=EXTRACTION_SYSTEM)

    # 4. Process entities — resolve or create
    entity_map: dict[str, str] = {}  # name -> entity_id
    entities_created = 0
    entities_resolved = 0
    extracted_at = _utc_now_iso()

    for raw_entity in extracted["entities"]:
        entity_name = raw_entity["name"]
        entity_type = raw_entity["type"]
        attributes = raw_entity.get("attributes", {})
        attributes["_source_doc_id"] = doc.id

        # Provenance metadata
        if session_id is not None:
            attributes["source_session_id"] = session_id
            attributes["extracted_at"] = extracted_at

        entity, was_created = resolve_or_create(
            db,
            input_name=entity_name,
            entity_type=entity_type,
            observer_id=observer_id,
            attributes=attributes,
        )
        entity_map[entity_name] = entity.id

        if was_created:
            entities_created += 1
        else:
            entities_resolved += 1

    # 5. Process relationships
    relationships_created = 0
    relationships_skipped = 0

    for raw_rel in extracted["relationships"]:
        source_name = raw_rel["source"]
        target_name = raw_rel["target"]

        # Both entities must exist in our map
        source_id = entity_map.get(source_name)
        target_id = entity_map.get(target_name)

        if source_id is None or target_id is None:
            relationships_skipped += 1
            continue

        rel_type = raw_rel["type"]
        directed = raw_rel.get("directed", True)
        rel_attrs = raw_rel.get("attributes", {})
        rel_attrs["_source_doc_id"] = doc.id

        # Provenance metadata
        if session_id is not None:
            rel_attrs["source_session_id"] = session_id
            rel_attrs["extracted_at"] = extracted_at

        # Skip if relationship already exists
        if db.relationship_exists(source_id, target_id, rel_type):
            relationships_skipped += 1
            continue

        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel_type,
            directed=directed,
            attributes=rel_attrs,
        )
        db.insert_relationship(rel)
        relationships_created += 1

    # 6. Orbit tracking — record interactions for all entities found
    if observer_id and entity_map:
        entity_ids = list(entity_map.values())
        bulk_record_interactions(db, observer_id, entity_ids)

    return {
        "document_id": doc.id,
        "session_id": session_id,
        "entities_created": entities_created,
        "entities_resolved": entities_resolved,
        "relationships_created": relationships_created,
        "relationships_skipped": relationships_skipped,
        "total_entities_extracted": len(extracted["entities"]),
        "total_relationships_extracted": len(extracted["relationships"]),
    }


def ingest_batch(
    db: GraphDB,
    texts: list[dict],
    schema_name: str | None = None,
    observer_id: str | None = None,
    session_id: str | None = None,
) -> list[dict]:
    """Ingest multiple texts.

    Each item should have 'text' and optionally 'source_type' and 'metadata'.

    Returns a list of summary dicts, one per text.
    """
    results = []
    for item in texts:
        result = ingest(
            db,
            text=item["text"],
            source_type=item.get("source_type", "text"),
            schema_name=schema_name,
            observer_id=observer_id,
            metadata=item.get("metadata"),
            session_id=session_id,
        )
        results.append(result)
    return results
