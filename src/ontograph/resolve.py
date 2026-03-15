"""Entity resolution: resolve ambiguous names to existing entities.

Uses a composite similarity score combining:
1. Phonetic similarity (Metaphone via jellyfish)
2. Spelling similarity (Jaro-Winkler distance)
3. Semantic similarity (embedding cosine distance)
4. Orbit proximity (interaction frequency weighting)

Solves the "Sam vs Sal" problem: your manager Sam gets transcribed as "Sal",
but orbit weighting ensures the correct resolution against all other Sals.
"""

from __future__ import annotations

import jellyfish
import numpy as np

from ontograph.config import RESOLUTION_THRESHOLD
from ontograph.db import GraphDB
from ontograph.llm import cosine_similarity, embed
from ontograph.models import Entity


def phonetic_similarity(a: str, b: str) -> float:
    """Compare two strings by their Metaphone phonetic encoding."""
    meta_a = jellyfish.metaphone(a.lower())
    meta_b = jellyfish.metaphone(b.lower())
    if meta_a == meta_b:
        return 1.0
    # Partial match on shared prefix
    max_len = max(len(meta_a), len(meta_b))
    if max_len == 0:
        return 0.0
    shared = 0
    for ca, cb in zip(meta_a, meta_b):
        if ca == cb:
            shared += 1
        else:
            break
    return shared / max_len


def spelling_similarity(a: str, b: str) -> float:
    """Jaro-Winkler string similarity (good for names with typos)."""
    return jellyfish.jaro_winkler_similarity(a.lower(), b.lower())


def semantic_similarity(
    name: str, entity_embedding: np.ndarray | None
) -> float:
    """Cosine similarity between the name's embedding and an entity's stored embedding."""
    if entity_embedding is None:
        return 0.0
    name_emb = embed(name)
    return cosine_similarity(name_emb, entity_embedding)


def compute_composite_score(
    input_name: str,
    candidate: Entity,
    candidate_embedding: np.ndarray | None,
    orbit_score: float = 0.0,
    alias_names: list[str] | None = None,
    weights: dict | None = None,
) -> float:
    """Compute a composite similarity score between an input name and a candidate entity.

    Components:
        phonetic:  0.20 — catches pronunciation-similar names (Dael ≈ Dale)
        spelling:  0.25 — catches typos and minor variations
        semantic:  0.30 — catches conceptually similar references
        orbit:     0.25 — weights by interaction frequency (closer = higher)

    If the input matches a known alias exactly, returns 1.0 immediately.
    """
    if weights is None:
        weights = {"phonetic": 0.20, "spelling": 0.25, "semantic": 0.30, "orbit": 0.25}

    # Check aliases first — exact match is a guaranteed resolution
    if alias_names:
        for alias in alias_names:
            if alias.lower() == input_name.lower():
                return 1.0

    # Compute individual scores
    phon = phonetic_similarity(input_name, candidate.name)
    spell = spelling_similarity(input_name, candidate.name)
    sem = semantic_similarity(input_name, candidate_embedding)

    # Also check best alias score (non-exact)
    best_alias_score = 0.0
    if alias_names:
        for alias in alias_names:
            alias_spell = spelling_similarity(input_name, alias)
            alias_phon = phonetic_similarity(input_name, alias)
            alias_score = max(alias_spell, alias_phon)
            best_alias_score = max(best_alias_score, alias_score)

    # Use best of (entity name score, alias score) for phonetic and spelling
    phon = max(phon, best_alias_score * 0.9)  # slight discount for alias match vs direct
    spell = max(spell, best_alias_score * 0.9)

    # Normalize orbit score to 0-1 range (already should be, but clamp)
    orbit_norm = min(max(orbit_score, 0.0), 1.0)

    composite = (
        weights["phonetic"] * phon
        + weights["spelling"] * spell
        + weights["semantic"] * sem
        + weights["orbit"] * orbit_norm
    )
    return composite


def resolve_entity(
    db: GraphDB,
    input_name: str,
    entity_type: str | None = None,
    observer_id: str | None = None,
    threshold: float = RESOLUTION_THRESHOLD,
) -> tuple[Entity | None, float]:
    """Attempt to resolve an input name to an existing entity in the graph.

    Returns (entity, score) if resolved above threshold, else (None, best_score).
    Logs every resolution attempt for the self-improving feedback loop.
    """
    # 1. Check exact name match
    exact = db.get_entity_by_name(input_name, entity_type)
    if exact is not None:
        db.log_resolution(input_name, exact.id, 1.0)
        return exact, 1.0

    # 2. Check alias exact match
    alias_match = db.find_entity_by_alias(input_name)
    if alias_match is not None:
        if entity_type is None or alias_match.entity_type == entity_type:
            db.log_resolution(input_name, alias_match.id, 1.0)
            return alias_match, 1.0

    # 3. Score all candidates
    candidates = db.list_entities(entity_type)
    if not candidates:
        db.log_resolution(input_name, None, 0.0)
        return None, 0.0

    best_entity: Entity | None = None
    best_score = 0.0

    for candidate in candidates:
        # Get orbit score for this candidate
        orbit_score = 0.0
        if observer_id:
            orbit_entry = db.get_orbit_entry(observer_id, candidate.id)
            if orbit_entry:
                orbit_score = orbit_entry.proximity_score

        # Get embedding
        candidate_embedding = db.get_entity_embedding(candidate.id)

        # Get aliases
        aliases = db.get_aliases(candidate.id)
        alias_names = [a.alias for a in aliases]

        score = compute_composite_score(
            input_name, candidate, candidate_embedding, orbit_score, alias_names
        )

        if score > best_score:
            best_score = score
            best_entity = candidate

    if best_score >= threshold and best_entity is not None:
        db.log_resolution(input_name, best_entity.id, best_score)
        return best_entity, best_score

    db.log_resolution(input_name, None, best_score)
    return None, best_score


def resolve_or_create(
    db: GraphDB,
    input_name: str,
    entity_type: str,
    observer_id: str | None = None,
    attributes: dict | None = None,
    threshold: float = RESOLUTION_THRESHOLD,
) -> tuple[Entity, bool]:
    """Resolve an entity name, creating a new entity if no match found.

    Returns (entity, was_created).
    """
    entity, score = resolve_entity(db, input_name, entity_type, observer_id, threshold)

    if entity is not None:
        return entity, False

    # Create new entity
    new_entity = Entity(
        name=input_name,
        entity_type=entity_type,
        attributes=attributes or {},
    )
    embedding = embed(f"{entity_type}: {input_name}")
    db.insert_entity(new_entity, embedding=embedding)
    return new_entity, True
