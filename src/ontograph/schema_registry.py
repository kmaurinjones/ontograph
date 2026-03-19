"""Pre-built schema definitions for common ontograph use cases.

The expanded schema includes entity types for decisions, goals, insights, and
sessions — plus relationship types for provenance tracking, blocking, and
cross-entity association.
"""

from __future__ import annotations

from ontograph.models import Schema

# ── Entity types ──

EXPANDED_ENTITY_TYPES: list[str] = [
    # Standard
    "person",
    "project",
    "organization",
    "topic",
    "event",
    "location",
    # Expanded
    "decision",
    "goal",
    "insight",
    "session",
]

# ── Relationship types ──

EXPANDED_RELATIONSHIP_TYPES: list[dict] = [
    # Standard
    {"name": "works_on", "directed": True},
    {"name": "belongs_to", "directed": True},
    {"name": "collaborates_with", "directed": False},
    {"name": "located_in", "directed": True},
    {"name": "mentioned_in", "directed": True},
    # Expanded — provenance
    {"name": "decided_during", "directed": True},      # decision → session
    {"name": "originated_in", "directed": True},        # any → session
    {"name": "updated_status", "directed": True},       # goal → session
    # Expanded — association
    {"name": "relates_to", "directed": True},           # any → project (generic)
    {"name": "blocks", "directed": True},               # goal/decision ↔ goal/decision
    {"name": "blocked_by", "directed": True},           # inverse of blocks
    {"name": "supports", "directed": True},             # insight → decision/goal
]

# ── Pre-built schema ──

EXPANDED_SCHEMA = Schema(
    name="expanded",
    entity_types=EXPANDED_ENTITY_TYPES,
    relationship_types=EXPANDED_RELATIONSHIP_TYPES,
)
