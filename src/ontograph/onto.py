"""OntoDB: the main entry point for ontograph.

Provides a clean, unified API over the knowledge graph. This is what users
import and interact with.

Usage:
    from ontograph import OntoDB, Schema

    db = OntoDB("my_knowledge.db")
    db.register_schema(Schema(
        name="workplace",
        entity_types=["person", "project", "team"],
        relationship_types=[
            {"name": "works_on", "directed": True},
            {"name": "colleague", "directed": False},
        ],
    ))

    result = db.ingest(
        "Meeting with Nara about Project Neptune. Marco joined from the remote office.",
        source_type="transcript",
        schema_name="workplace",
    )

    results = db.search("What is Nara working on?")
    answer = db.ask("Who works with Marco?")
"""

from __future__ import annotations

import os
from pathlib import Path

from ontograph.db import GraphDB
from ontograph.ingest import ingest as _ingest
from ontograph.ingest import ingest_batch as _ingest_batch
from ontograph.models import Alias, Entity, Relationship, Schema
from ontograph.orbit import get_orbit_ranked
from ontograph.resolve import resolve_entity
from ontograph.search import hybrid_search, search_and_answer


class OntoDB:
    """A knowledge graph database with LLM-powered ingestion and retrieval.

    Args:
        db_path: Path to the SQLite database file. Created if it doesn't exist.
        api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            Required for embeddings regardless of LLM provider.
        observer_id: Default observer entity ID for orbit tracking.
            If not set, orbit tracking requires explicit observer_id per call.
        llm_provider: LLM provider for generation calls ('openai' or 'google').
            If None, falls through to config files / env vars / default ('openai').
            Embeddings always use OpenAI regardless of this setting.
        llm_model: Override the LLM model name. If None, uses provider default.
        google_api_key: Google/Gemini API key. Falls back to GEMINI_API_KEY env var.
            Required when llm_provider='google'.
    """

    def __init__(
        self,
        db_path: str | Path = "ontograph.db",
        api_key: str | None = None,
        observer_id: str | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        google_api_key: str | None = None,
    ) -> None:
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        if google_api_key:
            os.environ["GEMINI_API_KEY"] = google_api_key

        from ontograph.config import set_llm_model, set_llm_provider

        if llm_provider is not None:
            set_llm_provider(llm_provider)
        if llm_model is not None:
            set_llm_model(llm_model)

        self._db = GraphDB(db_path)
        self._observer_id = observer_id

    def close(self) -> None:
        """Close the database connection."""
        self._db.close()

    def __enter__(self) -> OntoDB:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ── Schema ──

    def register_schema(self, schema: Schema) -> Schema:
        """Register an ontology schema defining valid entity and relationship types."""
        return self._db.insert_schema(schema)

    def get_schema(self, name: str) -> Schema | None:
        """Get a registered schema by name."""
        return self._db.get_schema(name)

    def list_schemas(self) -> list[Schema]:
        """List all registered schemas."""
        return self._db.list_schemas()

    # ── Entities ──

    def add_entity(
        self,
        name: str,
        entity_type: str,
        attributes: dict | None = None,
        aliases: list[dict] | None = None,
        file_refs: list[str] | None = None,
    ) -> Entity:
        """Manually add an entity to the graph.

        Args:
            name: Entity name
            entity_type: Type (e.g., 'person', 'project')
            attributes: Optional key-value attributes
            aliases: Optional list of {"alias": str, "type": str} dicts
            file_refs: Optional list of absolute file paths to associated files
        """
        from ontograph.llm import embed

        entity = Entity(
            name=name,
            entity_type=entity_type,
            attributes=attributes or {},
            file_refs=file_refs or [],
        )
        embedding = embed(f"{entity_type}: {name}")
        self._db.insert_entity(entity, embedding=embedding)

        if aliases:
            for alias_info in aliases:
                alias = Alias(
                    entity_id=entity.id,
                    alias=alias_info["alias"],
                    alias_type=alias_info["type"],
                )
                self._db.insert_alias(alias)

        return entity

    def attach_files(self, entity: str, file_paths: list[str]) -> Entity:
        """Attach file references to an existing entity.

        Appends to any existing file_refs without duplicating paths.

        Args:
            entity: Entity name or ID
            file_paths: Absolute file paths to attach
        """
        e = self.get_entity(entity)
        if e is None:
            raise ValueError(f"Entity not found: {entity}")
        merged = e.file_refs + [p for p in file_paths if p not in e.file_refs]
        self._db.update_entity_file_refs(e.id, merged)
        e.file_refs = merged
        return e

    def detach_files(self, entity: str, file_paths: list[str]) -> Entity:
        """Remove specific file references from an entity.

        Args:
            entity: Entity name or ID
            file_paths: File paths to remove
        """
        e = self.get_entity(entity)
        if e is None:
            raise ValueError(f"Entity not found: {entity}")
        remaining = [p for p in e.file_refs if p not in file_paths]
        self._db.update_entity_file_refs(e.id, remaining)
        e.file_refs = remaining
        return e

    def get_entity(self, name_or_id: str) -> Entity | None:
        """Get an entity by name or ID."""
        entity = self._db.get_entity(name_or_id)
        if entity is not None:
            return entity
        return self._db.get_entity_by_name(name_or_id)

    def list_entities(self, entity_type: str | None = None) -> list[Entity]:
        """List all entities, optionally filtered by type."""
        return self._db.list_entities(entity_type)

    def add_alias(self, entity_id: str, alias: str, alias_type: str = "alternate") -> Alias:
        """Add an alias (alternate name) for an entity.

        Use alias_type='transcript_error' for known transcription mistakes.
        """
        a = Alias(entity_id=entity_id, alias=alias, alias_type=alias_type)
        return self._db.insert_alias(a)

    # ── Relationships ──

    def add_relationship(
        self,
        source: str,
        target: str,
        relationship_type: str,
        directed: bool = True,
        attributes: dict | None = None,
    ) -> Relationship:
        """Manually add a relationship between two entities.

        source/target can be entity IDs or names.
        """
        source_entity = self.get_entity(source)
        target_entity = self.get_entity(target)
        if source_entity is None:
            raise ValueError(f"Source entity not found: {source}")
        if target_entity is None:
            raise ValueError(f"Target entity not found: {target}")

        rel = Relationship(
            source_id=source_entity.id,
            target_id=target_entity.id,
            relationship_type=relationship_type,
            directed=directed,
            attributes=attributes or {},
        )
        return self._db.insert_relationship(rel)

    def get_relationships(
        self, entity: str, relationship_type: str | None = None, direction: str | None = None
    ) -> list[Relationship]:
        """Get relationships for an entity (by name or ID)."""
        e = self.get_entity(entity)
        if e is None:
            return []
        return self._db.get_relationships(e.id, relationship_type, direction)

    def get_neighbors(self, entity: str, depth: int = 1) -> list[Entity]:
        """Get entities connected to the given entity within N hops."""
        e = self.get_entity(entity)
        if e is None:
            return []
        return self._db.get_neighbors(e.id, depth=depth)

    # ── Ingestion ──

    def ingest(
        self,
        text: str,
        source_type: str = "text",
        schema_name: str | None = None,
        observer_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Ingest unstructured text into the knowledge graph.

        The LLM extracts entities and relationships, resolves them against
        existing graph data, and creates new nodes/edges as needed.
        """
        obs = observer_id or self._observer_id
        return _ingest(self._db, text, source_type, schema_name, obs, metadata)

    def ingest_batch(
        self,
        texts: list[dict],
        schema_name: str | None = None,
        observer_id: str | None = None,
    ) -> list[dict]:
        """Ingest multiple texts. Each item: {"text": str, "source_type": str, "metadata": dict}."""
        obs = observer_id or self._observer_id
        return _ingest_batch(self._db, texts, schema_name, obs)

    # ── Search ──

    def search(
        self,
        query: str,
        limit: int = 10,
        graph_depth: int = 1,
    ) -> list[dict]:
        """Hybrid search: semantic + keyword + graph traversal."""
        return hybrid_search(self._db, query, limit=limit, graph_depth=graph_depth)

    def ask(
        self,
        question: str,
        limit: int = 10,
        graph_depth: int = 1,
    ) -> str:
        """Ask a question and get an LLM-synthesized answer from the knowledge graph."""
        result = search_and_answer(self._db, question, limit=limit, graph_depth=graph_depth)
        return result["answer"]

    def ask_with_sources(
        self,
        question: str,
        limit: int = 10,
        graph_depth: int = 1,
    ) -> dict:
        """Ask a question and get both the answer and the source entities/relationships."""
        return search_and_answer(self._db, question, limit=limit, graph_depth=graph_depth)

    # ── Orbit ──

    def orbit(self, observer: str | None = None, limit: int = 50) -> list[dict]:
        """Get the orbit (proximity-ranked entities) for an observer."""
        obs_id = observer or self._observer_id
        if obs_id is None:
            raise ValueError("No observer_id set. Pass one or set it in the constructor.")

        # Resolve name to ID if needed
        obs_entity = self.get_entity(obs_id)
        if obs_entity:
            obs_id = obs_entity.id

        entries = get_orbit_ranked(self._db, obs_id, limit=limit)
        results = []
        for entry, decayed_score in entries:
            entity = self._db.get_entity(entry.entity_id)
            if entity:
                results.append({
                    "entity": entity,
                    "proximity_score": round(decayed_score, 4),
                    "interaction_count": entry.interaction_count,
                    "last_interaction": entry.last_interaction,
                })
        return results

    # ── Entity resolution ──

    def resolve(
        self,
        name: str,
        entity_type: str | None = None,
        observer: str | None = None,
    ) -> tuple[Entity | None, float]:
        """Attempt to resolve a name to an existing entity.

        Returns (entity, confidence_score) or (None, best_score).
        """
        obs_id = observer or self._observer_id
        return resolve_entity(self._db, name, entity_type, obs_id)

    # ── Stats & admin ──

    def stats(self) -> dict:
        """Get graph statistics (entity, relationship, document, alias counts)."""
        stats = self._db.stats()
        stats["resolution_accuracy"] = self._db.get_resolution_accuracy()
        return stats

    def mark_resolution(self, log_id: str, correct: bool) -> None:
        """Mark a resolution log entry as correct or incorrect (feedback loop)."""
        self._db.mark_resolution_correct(log_id, correct)
