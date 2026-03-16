"""SQLite database layer for ontograph.

Tables:
    entities        — graph nodes (people, projects, topics, etc.)
    entity_aliases  — alternate names / transcription error mappings
    relationships   — directed or bidirectional edges between entities
    orbit           — interaction frequency and proximity tracking per observer
    documents       — ingested source material (transcripts, briefs, notes)
    schemas         — ontology schema definitions (valid types per domain)
    resolution_log  — entity resolution audit trail (self-improving feedback loop)
    entities_fts    — FTS5 full-text search over entity names and types
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from ontograph.models import Alias, Document, Entity, OrbitEntry, Relationship, Schema

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    attributes TEXT,
    embedding BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    directed INTEGER NOT NULL DEFAULT 1,
    attributes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orbit (
    id TEXT PRIMARY KEY,
    observer_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    interaction_count INTEGER DEFAULT 0,
    proximity_score REAL DEFAULT 0.0,
    last_interaction TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(observer_id, entity_id)
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL,
    metadata TEXT,
    embedding BLOB,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schemas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    entity_types TEXT NOT NULL,
    relationship_types TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resolution_log (
    id TEXT PRIMARY KEY,
    input_name TEXT NOT NULL,
    resolved_entity_id TEXT REFERENCES entities(id),
    similarity_score REAL,
    was_correct INTEGER,
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    name, entity_type, content=entities, content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
    INSERT INTO entities_fts(rowid, name, entity_type)
    VALUES (new.rowid, new.name, new.entity_type);
END;

CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
    UPDATE entities_fts SET name = new.name, entity_type = new.entity_type
    WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
    DELETE FROM entities_fts WHERE rowid = old.rowid;
END;

CREATE INDEX IF NOT EXISTS idx_aliases_entity ON entity_aliases(entity_id);
CREATE INDEX IF NOT EXISTS idx_aliases_alias ON entity_aliases(alias);
CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_orbit_observer ON orbit(observer_id);
CREATE INDEX IF NOT EXISTS idx_orbit_entity ON orbit(entity_id);
CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source_type);
"""


def _serialize_embedding(embedding: list[float] | np.ndarray | None) -> bytes | None:
    if embedding is None:
        return None
    arr = np.array(embedding, dtype=np.float32)
    return arr.tobytes()


def _deserialize_embedding(blob: bytes | None) -> np.ndarray | None:
    if blob is None:
        return None
    return np.frombuffer(blob, dtype=np.float32)


class GraphDB:
    """SQLite-backed knowledge graph storage."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """Apply schema migrations for backwards compatibility."""
        # v0.3.0: add file_refs column to entities
        try:
            self.conn.execute("ALTER TABLE entities ADD COLUMN file_refs TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

    def close(self) -> None:
        self.conn.close()

    # ── Entity CRUD ──

    def insert_entity(self, entity: Entity, embedding: list[float] | None = None) -> Entity:
        row = entity.to_row()
        self.conn.execute(
            "INSERT INTO entities "
            "(id, name, entity_type, attributes, file_refs, embedding, "
            "created_at, updated_at) "
            "VALUES (:id, :name, :entity_type, :attributes, :file_refs, "
            ":embedding, :created_at, :updated_at)",
            {**row, "embedding": _serialize_embedding(embedding)},
        )
        self.conn.commit()
        return entity

    def update_entity_file_refs(self, entity_id: str, file_refs: list[str]) -> None:
        """Update file references for an entity."""
        import json

        from ontograph.models import _now

        self.conn.execute(
            "UPDATE entities SET file_refs = ?, updated_at = ? WHERE id = ?",
            (json.dumps(file_refs), _now(), entity_id),
        )
        self.conn.commit()

    def get_entity(self, entity_id: str) -> Entity | None:
        row = self.conn.execute(
            "SELECT * FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()
        if row is None:
            return None
        return Entity.from_row(dict(row))

    def get_entity_by_name(self, name: str, entity_type: str | None = None) -> Entity | None:
        if entity_type:
            row = self.conn.execute(
                "SELECT * FROM entities WHERE LOWER(name) = LOWER(?) AND entity_type = ?",
                (name, entity_type),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM entities WHERE LOWER(name) = LOWER(?)", (name,)
            ).fetchone()
        if row is None:
            return None
        return Entity.from_row(dict(row))

    def get_entity_embedding(self, entity_id: str) -> np.ndarray | None:
        row = self.conn.execute(
            "SELECT embedding FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()
        if row is None:
            return None
        return _deserialize_embedding(row["embedding"])

    def update_entity_embedding(self, entity_id: str, embedding: list[float]) -> None:
        self.conn.execute(
            "UPDATE entities SET embedding = ? WHERE id = ?",
            (_serialize_embedding(embedding), entity_id),
        )
        self.conn.commit()

    def list_entities(self, entity_type: str | None = None) -> list[Entity]:
        if entity_type:
            rows = self.conn.execute(
                "SELECT * FROM entities WHERE entity_type = ? ORDER BY name", (entity_type,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM entities ORDER BY name").fetchall()
        return [Entity.from_row(dict(r)) for r in rows]

    def search_entities_fts(self, query: str, limit: int = 20) -> list[Entity]:
        rows = self.conn.execute(
            "SELECT e.* FROM entities e "
            "JOIN entities_fts f ON e.rowid = f.rowid "
            "WHERE entities_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [Entity.from_row(dict(r)) for r in rows]

    def get_all_entity_embeddings(self) -> list[tuple[str, np.ndarray]]:
        """Return (entity_id, embedding) for all entities that have embeddings."""
        rows = self.conn.execute(
            "SELECT id, embedding FROM entities WHERE embedding IS NOT NULL"
        ).fetchall()
        return [(r["id"], _deserialize_embedding(r["embedding"])) for r in rows]

    # ── Alias CRUD ──

    def insert_alias(self, alias: Alias) -> Alias:
        row = alias.to_row()
        self.conn.execute(
            "INSERT INTO entity_aliases (id, entity_id, alias, alias_type, created_at) "
            "VALUES (:id, :entity_id, :alias, :alias_type, :created_at)",
            row,
        )
        self.conn.commit()
        return alias

    def get_aliases(self, entity_id: str) -> list[Alias]:
        rows = self.conn.execute(
            "SELECT * FROM entity_aliases WHERE entity_id = ?", (entity_id,)
        ).fetchall()
        return [Alias.from_row(dict(r)) for r in rows]

    def find_entity_by_alias(self, alias_text: str) -> Entity | None:
        row = self.conn.execute(
            "SELECT e.* FROM entities e "
            "JOIN entity_aliases a ON e.id = a.entity_id "
            "WHERE LOWER(a.alias) = LOWER(?)",
            (alias_text,),
        ).fetchone()
        if row is None:
            return None
        return Entity.from_row(dict(row))

    # ── Relationship CRUD ──

    def insert_relationship(self, rel: Relationship) -> Relationship:
        row = rel.to_row()
        self.conn.execute(
            "INSERT INTO relationships (id, source_id, target_id, "
            "relationship_type, directed, attributes, "
            "created_at, updated_at) "
            "VALUES (:id, :source_id, :target_id, "
            ":relationship_type, :directed, :attributes, "
            ":created_at, :updated_at)",
            row,
        )
        self.conn.commit()
        return rel

    def get_relationships(
        self,
        entity_id: str,
        relationship_type: str | None = None,
        direction: str | None = None,
    ) -> list[Relationship]:
        """Get relationships involving an entity.

        direction: 'outgoing' (entity is source), 'incoming' (entity is target), None (both)
        """
        conditions = []
        params: list = []

        if direction == "outgoing":
            conditions.append("source_id = ?")
            params.append(entity_id)
        elif direction == "incoming":
            conditions.append("target_id = ?")
            params.append(entity_id)
        else:
            conditions.append(
                "(source_id = ? OR target_id = ? "
                "OR (directed = 0 AND (source_id = ? OR target_id = ?)))"
            )
            params.extend([entity_id, entity_id, entity_id, entity_id])

        if relationship_type:
            conditions.append("relationship_type = ?")
            params.append(relationship_type)

        where = " AND ".join(conditions)
        rows = self.conn.execute(
            f"SELECT * FROM relationships WHERE {where} ORDER BY created_at DESC",
            params,
        ).fetchall()
        return [Relationship.from_row(dict(r)) for r in rows]

    def relationship_exists(
        self, source_id: str, target_id: str, relationship_type: str
    ) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM relationships "
            "WHERE source_id = ? AND target_id = ? "
            "AND relationship_type = ?",
            (source_id, target_id, relationship_type),
        ).fetchone()
        return row is not None

    # ── Orbit CRUD ──

    def upsert_orbit(self, entry: OrbitEntry) -> OrbitEntry:
        row = entry.to_row()
        self.conn.execute(
            "INSERT INTO orbit (id, observer_id, entity_id, interaction_count, proximity_score, "
            "last_interaction, created_at, updated_at) "
            "VALUES (:id, :observer_id, :entity_id, :interaction_count, :proximity_score, "
            ":last_interaction, :created_at, :updated_at) "
            "ON CONFLICT(observer_id, entity_id) DO UPDATE SET "
            "interaction_count = interaction_count + excluded.interaction_count, "
            "proximity_score = excluded.proximity_score, "
            "last_interaction = excluded.last_interaction, "
            "updated_at = excluded.updated_at",
            row,
        )
        self.conn.commit()
        return entry

    def get_orbit(self, observer_id: str, limit: int = 50) -> list[OrbitEntry]:
        rows = self.conn.execute(
            "SELECT * FROM orbit WHERE observer_id = ? ORDER BY proximity_score DESC LIMIT ?",
            (observer_id, limit),
        ).fetchall()
        return [OrbitEntry.from_row(dict(r)) for r in rows]

    def get_orbit_entry(self, observer_id: str, entity_id: str) -> OrbitEntry | None:
        row = self.conn.execute(
            "SELECT * FROM orbit WHERE observer_id = ? AND entity_id = ?",
            (observer_id, entity_id),
        ).fetchone()
        if row is None:
            return None
        return OrbitEntry.from_row(dict(row))

    # ── Document CRUD ──

    def insert_document(self, doc: Document, embedding: list[float] | None = None) -> Document:
        row = doc.to_row()
        self.conn.execute(
            "INSERT INTO documents (id, content, source_type, metadata, embedding, created_at) "
            "VALUES (:id, :content, :source_type, :metadata, :embedding, :created_at)",
            {**row, "embedding": _serialize_embedding(embedding)},
        )
        self.conn.commit()
        return doc

    def get_document(self, doc_id: str) -> Document | None:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            return None
        return Document.from_row(dict(row))

    # ── Schema CRUD ──

    def insert_schema(self, schema: Schema) -> Schema:
        row = schema.to_row()
        self.conn.execute(
            "INSERT OR REPLACE INTO schemas "
            "(id, name, entity_types, relationship_types, created_at, updated_at) "
            "VALUES (:id, :name, :entity_types, :relationship_types, :created_at, :updated_at)",
            row,
        )
        self.conn.commit()
        return schema

    def get_schema(self, name: str) -> Schema | None:
        row = self.conn.execute(
            "SELECT * FROM schemas WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        return Schema.from_row(dict(row))

    def list_schemas(self) -> list[Schema]:
        rows = self.conn.execute("SELECT * FROM schemas ORDER BY name").fetchall()
        return [Schema.from_row(dict(r)) for r in rows]

    # ── Resolution log ──

    def log_resolution(
        self,
        input_name: str,
        resolved_entity_id: str | None,
        similarity_score: float | None,
    ) -> None:
        from ontograph.models import _now, _uuid

        self.conn.execute(
            "INSERT INTO resolution_log "
            "(id, input_name, resolved_entity_id, "
            "similarity_score, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (_uuid(), input_name, resolved_entity_id, similarity_score, _now()),
        )
        self.conn.commit()

    def mark_resolution_correct(self, log_id: str, correct: bool) -> None:
        self.conn.execute(
            "UPDATE resolution_log SET was_correct = ? WHERE id = ?",
            (int(correct), log_id),
        )
        self.conn.commit()

    def get_resolution_accuracy(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct, "
            "SUM(CASE WHEN was_correct = 0 THEN 1 ELSE 0 END) as incorrect "
            "FROM resolution_log WHERE was_correct IS NOT NULL"
        ).fetchone()
        total = row["total"]
        if total == 0:
            return {"total": 0, "correct": 0, "incorrect": 0, "accuracy": None}
        return {
            "total": total,
            "correct": row["correct"],
            "incorrect": row["incorrect"],
            "accuracy": row["correct"] / total,
        }

    # ── Graph traversal ──

    def get_neighbors(self, entity_id: str, depth: int = 1) -> list[Entity]:
        """Get entities connected to the given entity within N hops."""
        visited: set[str] = {entity_id}
        frontier: set[str] = {entity_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for eid in frontier:
                rows = self.conn.execute(
                    "SELECT CASE WHEN source_id = ? "
                    "THEN target_id ELSE source_id END as neighbor_id "
                    "FROM relationships "
                    "WHERE source_id = ? OR target_id = ?",
                    (eid, eid, eid),
                ).fetchall()
                for r in rows:
                    nid = r["neighbor_id"]
                    if nid not in visited:
                        visited.add(nid)
                        next_frontier.add(nid)
            frontier = next_frontier

        visited.discard(entity_id)
        if not visited:
            return []

        placeholders = ",".join("?" for _ in visited)
        rows = self.conn.execute(
            f"SELECT * FROM entities WHERE id IN ({placeholders})", list(visited)
        ).fetchall()
        return [Entity.from_row(dict(r)) for r in rows]

    # ── Stats ──

    def stats(self) -> dict:
        entity_count = self.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        rel_count = self.conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        doc_count = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        alias_count = self.conn.execute("SELECT COUNT(*) FROM entity_aliases").fetchone()[0]
        return {
            "entities": entity_count,
            "relationships": rel_count,
            "documents": doc_count,
            "aliases": alias_count,
        }
