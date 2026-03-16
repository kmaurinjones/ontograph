"""Hybrid search: semantic + keyword + graph traversal.

Three retrieval strategies combined:
1. Semantic: embed the query, find nearest entity/document embeddings
2. Keyword: FTS5 full-text search over entity names and types
3. Graph: traverse relationships from matched entities to find connected context

Results are ranked by a composite score and optionally filtered by the LLM
for relevance to the original query.
"""

from __future__ import annotations

from ontograph.db import GraphDB
from ontograph.llm import cosine_similarity, embed, llm_call
from ontograph.models import Entity, Relationship


def _semantic_search(
    db: GraphDB, query_embedding: list[float], limit: int
) -> list[tuple[Entity, float]]:
    """Find entities closest to the query embedding by cosine similarity."""
    all_embeddings = db.get_all_entity_embeddings()
    if not all_embeddings:
        return []

    scored: list[tuple[str, float]] = []
    for entity_id, emb in all_embeddings:
        if emb is not None:
            sim = cosine_similarity(query_embedding, emb)
            scored.append((entity_id, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:limit]

    results = []
    for entity_id, score in top:
        entity = db.get_entity(entity_id)
        if entity is not None:
            results.append((entity, score))
    return results


def _keyword_search(db: GraphDB, query: str, limit: int) -> list[Entity]:
    """FTS5 keyword search over entity names and types."""
    # FTS5 query syntax — quote the query to handle special chars
    fts_query = " OR ".join(f'"{word}"' for word in query.split() if word.strip())
    if not fts_query:
        return []
    return db.search_entities_fts(fts_query, limit=limit)


def _graph_expand(
    db: GraphDB, seed_entities: list[Entity], depth: int = 1
) -> list[tuple[Entity, list[Relationship]]]:
    """Expand from seed entities through the graph, returning neighbors with their relationships."""
    results: list[tuple[Entity, list[Relationship]]] = []
    seen: set[str] = {e.id for e in seed_entities}

    for seed in seed_entities:
        neighbors = db.get_neighbors(seed.id, depth=depth)
        for neighbor in neighbors:
            if neighbor.id not in seen:
                seen.add(neighbor.id)
                rels = db.get_relationships(neighbor.id)
                results.append((neighbor, rels))

    return results


def hybrid_search(
    db: GraphDB,
    query: str,
    limit: int = 10,
    semantic_weight: float = 0.5,
    keyword_weight: float = 0.3,
    graph_weight: float = 0.2,
    graph_depth: int = 1,
) -> list[dict]:
    """Hybrid search combining semantic, keyword, and graph retrieval.

    Returns a list of result dicts, each containing:
        - entity: the matched Entity
        - score: composite relevance score
        - source: how it was found ('semantic', 'keyword', 'graph')
        - relationships: list of connected Relationships
    """
    query_embedding = embed(query)
    entity_scores: dict[str, dict] = {}

    # 1. Semantic search
    semantic_results = _semantic_search(db, query_embedding, limit=limit * 2)
    for entity, sim_score in semantic_results:
        entity_scores[entity.id] = {
            "entity": entity,
            "semantic": sim_score,
            "keyword": 0.0,
            "graph": 0.0,
            "source": "semantic",
        }

    # 2. Keyword search
    keyword_results = _keyword_search(db, query, limit=limit * 2)
    for i, entity in enumerate(keyword_results):
        # Score by rank position (1.0 for top, decaying)
        kw_score = 1.0 / (1 + i)
        if entity.id in entity_scores:
            entity_scores[entity.id]["keyword"] = kw_score
            entity_scores[entity.id]["source"] = "semantic+keyword"
        else:
            entity_scores[entity.id] = {
                "entity": entity,
                "semantic": 0.0,
                "keyword": kw_score,
                "graph": 0.0,
                "source": "keyword",
            }

    # 3. Graph expansion from top semantic+keyword hits
    seed_ids = sorted(entity_scores.keys(), key=lambda eid: (
        entity_scores[eid]["semantic"] * semantic_weight
        + entity_scores[eid]["keyword"] * keyword_weight
    ), reverse=True)[:5]

    seed_entities = [entity_scores[eid]["entity"] for eid in seed_ids if eid in entity_scores]
    graph_results = _graph_expand(db, seed_entities, depth=graph_depth)

    for entity, rels in graph_results:
        graph_score = 0.5  # base graph discovery score
        if entity.id in entity_scores:
            entity_scores[entity.id]["graph"] = graph_score
            if "graph" not in entity_scores[entity.id]["source"]:
                entity_scores[entity.id]["source"] += "+graph"
        else:
            entity_scores[entity.id] = {
                "entity": entity,
                "semantic": 0.0,
                "keyword": 0.0,
                "graph": graph_score,
                "source": "graph",
            }

    # 4. Compute composite scores and rank
    ranked = []
    for eid, data in entity_scores.items():
        composite = (
            data["semantic"] * semantic_weight
            + data["keyword"] * keyword_weight
            + data["graph"] * graph_weight
        )
        rels = db.get_relationships(eid)
        ranked.append({
            "entity": data["entity"],
            "score": round(composite, 4),
            "source": data["source"],
            "relationships": rels,
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:limit]


def search_and_answer(
    db: GraphDB,
    query: str,
    limit: int = 10,
    graph_depth: int = 1,
) -> dict:
    """Search the graph and generate an LLM-synthesized answer.

    This is the "smart retrieval" path: it decides what context is needed,
    retrieves it from the graph, and synthesizes a natural language answer.

    Returns:
        - answer: the LLM-generated response
        - sources: the entities and relationships used
    """
    results = hybrid_search(db, query, limit=limit, graph_depth=graph_depth)

    if not results:
        return {
            "answer": "No relevant information found in the knowledge graph.",
            "sources": [],
        }

    # Build context from search results
    context_parts = []
    for r in results:
        entity = r["entity"]
        part = f"Entity: {entity.name} (type: {entity.entity_type})"
        if entity.attributes:
            part += f"\n  Attributes: {entity.attributes}"
        if entity.file_refs:
            part += f"\n  Referenced files: {entity.file_refs}"

        rel_descriptions = []
        for rel in r["relationships"]:
            source = db.get_entity(rel.source_id)
            target = db.get_entity(rel.target_id)
            if source and target:
                arrow = "→" if rel.directed else "↔"
                rel_descriptions.append(
                    f"  {source.name} {arrow} {target.name} [{rel.relationship_type}]"
                )
        if rel_descriptions:
            part += "\n  Relationships:\n" + "\n".join(rel_descriptions)

        context_parts.append(part)

    context = "\n\n".join(context_parts)

    answer = llm_call(
        f"Based on the following knowledge graph context, answer the question.\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {query}\n\n"
        f"Answer concisely using only information from the context. "
        f"If the context doesn't contain enough information, say so.",
        system="You are a knowledge graph query assistant. Answer questions using only "
        "the provided graph context. Be precise and cite specific entities and relationships.",
    )

    return {
        "answer": answer,
        "sources": results,
    }
