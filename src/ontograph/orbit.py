"""Orbit tracking: ontological proximity scoring.

The orbit is a weighted proximity model around an observer entity.
Entities you interact with frequently have higher orbit scores.
This powers entity resolution — when "Sal" appears in a transcript,
the system checks who in your orbit is closest to "Sal" and weights
accordingly.

Orbit scores decay over time (configurable) so stale connections
don't dominate. Recent, frequent interactions score highest.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from ontograph.config import ORBIT_DECAY_FACTOR
from ontograph.db import GraphDB
from ontograph.models import OrbitEntry, _now


def record_interaction(
    db: GraphDB,
    observer_id: str,
    entity_id: str,
    interaction_weight: float = 1.0,
) -> OrbitEntry:
    """Record an interaction between observer and entity, updating orbit scores.

    Each interaction increments the count and recalculates proximity_score
    with time decay applied.
    """
    existing = db.get_orbit_entry(observer_id, entity_id)
    now = _now()

    if existing is None:
        entry = OrbitEntry(
            observer_id=observer_id,
            entity_id=entity_id,
            interaction_count=1,
            proximity_score=interaction_weight,
            last_interaction=now,
        )
    else:
        # Apply time decay to existing score
        decayed_score = _apply_decay(
            existing.proximity_score, existing.last_interaction
        )
        new_score = min(decayed_score + interaction_weight, 1.0)

        entry = OrbitEntry(
            observer_id=observer_id,
            entity_id=entity_id,
            interaction_count=1,  # upsert adds to existing count
            proximity_score=new_score,
            last_interaction=now,
        )

    db.upsert_orbit(entry)
    return entry


def _apply_decay(score: float, last_interaction: str | None) -> float:
    """Apply exponential time decay to a proximity score.

    Score decays by ORBIT_DECAY_FACTOR per day since last interaction.
    """
    if last_interaction is None:
        return score

    try:
        last_dt = datetime.fromisoformat(last_interaction)
        now_dt = datetime.now(timezone.utc)
        days_elapsed = (now_dt - last_dt).total_seconds() / 86400
        decay = math.pow(ORBIT_DECAY_FACTOR, days_elapsed)
        return score * decay
    except (ValueError, TypeError):
        return score


def get_orbit_ranked(
    db: GraphDB, observer_id: str, limit: int = 50
) -> list[tuple[OrbitEntry, float]]:
    """Get orbit entries ranked by decayed proximity score.

    Returns list of (entry, decayed_score) tuples.
    """
    # Over-fetch to account for decay reranking
    entries = db.get_orbit(observer_id, limit=limit * 2)
    scored = []
    for entry in entries:
        decayed = _apply_decay(entry.proximity_score, entry.last_interaction)
        scored.append((entry, decayed))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def bulk_record_interactions(
    db: GraphDB,
    observer_id: str,
    entity_ids: list[str],
    interaction_weight: float = 1.0,
) -> None:
    """Record interactions with multiple entities at once (e.g., all participants in a meeting)."""
    for entity_id in entity_ids:
        if entity_id != observer_id:
            record_interaction(db, observer_id, entity_id, interaction_weight)
