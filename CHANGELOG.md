# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-19

### Added
- Expanded schema with 4 new entity types: `decision`, `goal`, `insight`, `session`
- 7 new directed relationship types: `decided_during`, `relates_to`, `blocks`, `blocked_by`, `supports`, `originated_in`, `updated_status`
- Pre-built `EXPANDED_SCHEMA` constant with all standard + new types, registerable via `register_schema()`
- `EXPANDED_ENTITY_TYPES` and `EXPANDED_RELATIONSHIP_TYPES` constants in `schema_registry` module
- Temporal normalization utility (`normalize_temporal()`) — converts relative time references ("next quarter", "by July 2026", "Q3 2026", "this week") to ISO dates
- Provenance metadata on ingestion — `session_id` parameter on `ingest()` stamps all entities and relationships with `source_session_id` and `extracted_at`
- Enriched attributes pattern in LLM extraction prompt: `status`, `confidence`, `temporal`, `source_project`
- `EXPANDED_SCHEMA` and `normalize_temporal` exported from package root
- 34 new tests across temporal normalization, expanded schema validation, and ingest provenance

### Changed
- LLM extraction prompt now explicitly asks for decisions, goals, insights, and sessions
- `ingest()` and `ingest_batch()` accept optional `session_id` parameter
- Ingest return dict includes `session_id` field

## [0.4.0] - 2026-03-19

### Added
- Google Gemini LLM support — use `gemini-2.5-flash-lite` (or any Gemini model) as an alternative to OpenAI for all LLM generation calls
- YAML-based config system with 5-layer precedence: constructor kwargs > env vars > project config (`.ontograph/config.yaml`) > user config (`~/.ontograph/config.yaml`) > hardcoded defaults
- `set_llm_provider()`, `set_llm_model()`, `set_embedding_model()`, `set_embedding_dimensions()` runtime config setters
- `ONTOGRAPH_LLM_PROVIDER`, `ONTOGRAPH_LLM_MODEL`, `ONTOGRAPH_EMBEDDINGS_MODEL`, `ONTOGRAPH_EMBEDDINGS_DIMENSIONS` environment variable overrides
- `llm_provider`, `llm_model`, `google_api_key` parameters on `OntoDB` constructor
- `reload_configs()` to force re-read config files from disk
- 26 new tests for config precedence, YAML loading, runtime overrides, env vars

### Changed
- `config.py` rewritten to support multi-source config resolution (was single-source env vars)
- `llm.py` uses dynamic getter functions instead of imported constants for model/provider selection
- Embeddings remain OpenAI-only regardless of LLM provider setting

## [0.3.0] - 2026-03-15

### Added
- File references on entities (`file_refs`) — attach external files (PDFs, images, receipts) to entities without storing binary data in the DB
- `ontograph attach` CLI command — link files to entities by name or ID
- `ontograph detach` CLI command — remove file references from entities
- `--file-refs` flag on `add-entity` for creating entities with file references
- File references surfaced in search context so the LLM can reference them in answers
- File references shown in dashboard sidebar
- Auto-migration for existing databases (adds `file_refs` column)
- Home renovation example (`examples/home_renovation.py`) demonstrating file references
- 9 new tests for file references (model, DB, CLI)

## [0.2.0] - 2026-03-15

### Added
- Interactive knowledge graph dashboard (`ontograph dashboard`) with D3.js force-directed visualization
- Lazy-loading graph expansion — starts with the most-connected hub node and top 50 relationships
- Click to select, double-click to expand, drag to reposition, scroll to zoom
- Dashboard API endpoints (`/api/stats`, `/api/hub`, `/api/expand/<id>`)
- Dark theme with entity-type color coding and relationship labels
- CLI command with `--port`, `--host`, and `--no-browser` flags

## [0.1.1] - 2026-03-15

### Added
- Full CLI (`ontograph` command) with 14 subcommands: `stats`, `ingest`, `search`, `ask`, `entities`, `entity`, `relationships`, `neighbors`, `resolve`, `orbit`, `add-entity`, `add-relationship`, `add-alias`, `schema`
- JSON output by default for all commands (pipe-friendly for LLM tool use)
- stdin support for `ingest` and `schema register` (pipe text or JSON)
- Detailed `--help` with usage examples on every subcommand
- `python-dotenv` integration — `.env` files loaded automatically
- Console entry point (`[project.scripts]`) for global `ontograph` command

### Changed
- Replaced all example names in docs, help text, and tests with generic placeholders

## [0.1.0] - 2026-03-15

### Added
- Initial release: LLM-powered knowledge graph engine
- `OntoDB` Python API — unified interface over the knowledge graph
- SQLite-backed storage with FTS5 full-text search
- LLM-driven entity and relationship extraction from unstructured text
- Composite entity resolution (phonetic, spelling, semantic, orbit proximity)
- Orbit-based proximity scoring with time decay
- Hybrid search (semantic + keyword + graph traversal)
- LLM-synthesized Q&A over graph context (`ask` / `ask_with_sources`)
- Schema-constrained extraction to limit valid entity/relationship types
- Resolution audit log with feedback loop
- 26 tests covering DB, models, and entity resolution
