"""Core domain models: Entity, Relationship, Schema.

Every piece of information decomposes into entities, relationships, and attributes.
OOP 100% — each concept is a first-class object.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Entity:
    """A node in the knowledge graph. People, projects, topics, orgs — anything nameable.

    file_refs stores absolute file paths to external files associated with this
    entity (receipts, images, PDFs, contracts, etc.). These are pointers only —
    the files themselves live on disk, not in the database.
    """

    name: str
    entity_type: str
    id: str = field(default_factory=_uuid)
    attributes: dict = field(default_factory=dict)
    file_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "attributes": json.dumps(self.attributes),
            "file_refs": json.dumps(self.file_refs),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> Entity:
        file_refs_raw = row["file_refs"] if "file_refs" in dict(row) else None
        return cls(
            id=row["id"],
            name=row["name"],
            entity_type=row["entity_type"],
            attributes=json.loads(row["attributes"]) if row["attributes"] else {},
            file_refs=json.loads(file_refs_raw) if file_refs_raw else [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class Relationship:
    """A directed or bidirectional edge between two entities.

    Examples:
        node_a -> node_b [works_on]              (directed)
        node_a <-> node_b [collaborates_with]    (bidirectional)
    """

    source_id: str
    target_id: str
    relationship_type: str
    directed: bool = True
    id: str = field(default_factory=_uuid)
    attributes: dict = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    @property
    def direction(self) -> str:
        return "directed" if self.directed else "bidirectional"

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "directed": int(self.directed),
            "attributes": json.dumps(self.attributes),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> Relationship:
        return cls(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relationship_type=row["relationship_type"],
            directed=bool(row["directed"]),
            attributes=json.loads(row["attributes"]) if row["attributes"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class Alias:
    """An alternate name for an entity. Handles transcription errors, nicknames, etc.

    alias_type examples: 'transcript_error', 'nickname', 'alternate_spelling', 'abbreviation'
    """

    entity_id: str
    alias: str
    alias_type: str
    id: str = field(default_factory=_uuid)
    created_at: str = field(default_factory=_now)

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "alias": self.alias,
            "alias_type": self.alias_type,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> Alias:
        return cls(
            id=row["id"],
            entity_id=row["entity_id"],
            alias=row["alias"],
            alias_type=row["alias_type"],
            created_at=row["created_at"],
        )


@dataclass
class Schema:
    """An ontology schema defining valid entity types and relationship types for a domain.

    Schemas constrain what the LLM can extract — they define the vocabulary of
    the knowledge graph for a specific domain.
    """

    name: str
    entity_types: list[str]
    relationship_types: list[dict]  # [{"name": str, "directed": bool}, ...]
    id: str = field(default_factory=_uuid)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "entity_types": json.dumps(self.entity_types),
            "relationship_types": json.dumps(self.relationship_types),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> Schema:
        return cls(
            id=row["id"],
            name=row["name"],
            entity_types=json.loads(row["entity_types"]),
            relationship_types=json.loads(row["relationship_types"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @property
    def relationship_type_names(self) -> list[str]:
        return [r["name"] for r in self.relationship_types]


@dataclass
class OrbitEntry:
    """Tracks interaction frequency and proximity between an observer and another entity.

    The 'orbit' concept: entities closer in your orbit (higher interaction frequency)
    get weighted more heavily during entity resolution. Solves the "Sam vs Sal" problem —
    your manager Sam is in your orbit, random Sals across the company are not.
    """

    observer_id: str
    entity_id: str
    interaction_count: int = 0
    proximity_score: float = 0.0
    last_interaction: str | None = None
    id: str = field(default_factory=_uuid)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "observer_id": self.observer_id,
            "entity_id": self.entity_id,
            "interaction_count": self.interaction_count,
            "proximity_score": self.proximity_score,
            "last_interaction": self.last_interaction,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> OrbitEntry:
        return cls(
            id=row["id"],
            observer_id=row["observer_id"],
            entity_id=row["entity_id"],
            interaction_count=row["interaction_count"],
            proximity_score=row["proximity_score"],
            last_interaction=row["last_interaction"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class Document:
    """A source document that was ingested. Transcripts, briefs, notes, etc."""

    content: str
    source_type: str
    id: str = field(default_factory=_uuid)
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "source_type": self.source_type,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> Document:
        return cls(
            id=row["id"],
            content=row["content"],
            source_type=row["source_type"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
        )
