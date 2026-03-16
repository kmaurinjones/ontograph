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

### File References
Entities can reference external files — receipts, photos, PDFs, contracts — that live on disk rather than in the database. These references are surfaced during search and Q&A so the LLM knows where to find supporting material.

```python
# Attach files to an entity
db.attach_files("kitchen renovation", [
    "/Users/me/photos/kitchen_before.jpg",
    "/Users/me/photos/kitchen_after.jpg",
])

# Or via CLI
# ontograph attach "kitchen renovation" /Users/me/photos/kitchen_before.jpg
```

```python
# When you ask a question, the LLM sees the file references
answer = db.ask("What photos do we have of the kitchen?")
# → "There are two referenced photos: kitchen_before.jpg and kitchen_after.jpg at /Users/me/photos/"
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
- `.add_entity(name, entity_type, attributes, aliases, file_refs) → Entity` — Manual entity creation
- `.add_relationship(source, target, type, directed) → Relationship` — Manual relationship creation
- `.attach_files(entity, file_paths) → Entity` — Attach file references to an entity
- `.detach_files(entity, file_paths) → Entity` — Remove file references from an entity
- `.resolve(name, entity_type, observer) → (Entity | None, float)` — Entity resolution
- `.orbit(observer, limit) → list[dict]` — Proximity-ranked entities
- `.stats() → dict` — Graph statistics and resolution accuracy

## CLI

```bash
ontograph --help                  # Full command list
ontograph ingest --text "..."     # Ingest text
ontograph search "query"          # Hybrid search
ontograph ask "question"          # LLM-synthesized answer
ontograph entities                # List entities
ontograph attach "entity" file.pdf  # Attach files to entity
ontograph detach "entity" file.pdf  # Remove file references
ontograph dashboard               # Interactive graph visualization
```

## Dashboard

```bash
ontograph dashboard               # Opens browser at http://127.0.0.1:8484
ontograph dashboard --port 9000   # Custom port
ontograph --db project.db dashboard
```

Interactive force-directed graph visualization. Starts with the most-connected
entity as hub. Click to select, double-click to expand, drag to reposition,
scroll to zoom.
