# ontograph

LLM-powered knowledge graph engine with ontological entity resolution, orbit-based proximity scoring, and hybrid semantic-graph retrieval.

## Install

```bash
pip install ontograph
# or from source:
uv add .
```

Requires `OPENAI_API_KEY` environment variable.

## Quick Start

```python
from ontograph import OntoDB, Schema

# Initialize — creates a local SQLite database
db = OntoDB("my_knowledge.db")

# Define an ontology schema (constrains what the LLM extracts)
db.register_schema(Schema(
    name="workplace",
    entity_types=["person", "project", "team", "meeting", "topic"],
    relationship_types=[
        {"name": "works_on", "directed": True},
        {"name": "manages", "directed": True},
        {"name": "colleague", "directed": False},
        {"name": "discussed", "directed": True},
        {"name": "member_of", "directed": True},
    ],
))

# Ingest unstructured text — entities and relationships extracted automatically
db.ingest(
    "Meeting with Nara and Marco about Project Neptune. "
    "Nara is leading the backend rewrite. Marco raised concerns about the launch deadline.",
    source_type="transcript",
    schema_name="workplace",
)

# Search the graph (semantic + keyword + graph traversal)
results = db.search("What is Nara working on?")

# Ask a question — LLM synthesizes answer from graph context
answer = db.ask("Who is concerned about the launch deadline?")
print(answer)
```

## Core Concepts

### Entities, Relationships, Attributes
Everything decomposes into these three primitives:
- **Entities**: nodes — people, projects, topics, anything nameable
- **Relationships**: edges — directed (`A → B`) or bidirectional (`A ↔ B`)
- **Attributes**: key-value metadata on entities and relationships

### Entity Resolution
When ingesting text, names are fuzzy-matched against existing entities using a composite score:
- **Phonetic similarity** (Metaphone) — catches pronunciation-similar names
- **Spelling similarity** (Jaro-Winkler) — catches typos
- **Semantic similarity** (embedding cosine) — catches conceptual matches
- **Orbit proximity** — weights by interaction frequency

### Orbit
Your "orbit" is a proximity model. Entities you interact with frequently score higher. This powers entity resolution — when "Sal" appears in a transcript, the system weights your manager "Sam" (who you interact with daily) over random "Sal"s elsewhere.

```python
# Add a known transcription error alias
sam = db.get_entity("Sam")
db.add_alias(sam.id, "Sal", alias_type="transcript_error")
```

### Schemas
Ontology schemas define valid entity and relationship types for a domain. They constrain what the LLM extracts.

### Self-Improving Feedback Loop
Every entity resolution is logged. Mark resolutions as correct/incorrect to track accuracy over time:

```python
db.mark_resolution("log_id", correct=True)
print(db.stats()["resolution_accuracy"])
```

## API

- `OntoDB(db_path, api_key=None, observer_id=None)` — Main entry point
- `.ingest(text, source_type, schema_name, observer_id, metadata) → dict` — Ingest unstructured text
- `.search(query, limit, graph_depth) → list[dict]` — Hybrid search
- `.ask(question) → str` — LLM-synthesized answer from graph context
- `.add_entity(name, entity_type, attributes, aliases) → Entity` — Manual entity creation
- `.add_relationship(source, target, type, directed) → Relationship` — Manual relationship creation
- `.resolve(name, entity_type, observer) → (Entity | None, float)` — Entity resolution
- `.orbit(observer, limit) → list[dict]` — Proximity-ranked entities
- `.stats() → dict` — Graph statistics and resolution accuracy
