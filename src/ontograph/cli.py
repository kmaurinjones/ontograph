"""ontograph CLI — command-line interface for the ontograph knowledge graph engine.

Provides subcommands for every core operation: ingesting text, searching the
graph, asking questions, managing entities/relationships/schemas, entity
resolution, and orbit proximity tracking.

All output is JSON by default, making it straightforward for LLMs and scripts
to parse. Human-readable table output is available via --format=table on
commands that support it.

Requires:
    OPENAI_API_KEY environment variable set for any operation that calls the LLM
    or embedding model (ingest, search, ask, resolve, add-entity).

Usage:
    ontograph --help
    ontograph <command> --help
    ontograph stats --db my_graph.db
    echo "Meeting notes here..." | ontograph ingest --source-type transcript
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ontograph import __version__
from ontograph.models import Schema
from ontograph.onto import OntoDB

# ── JSON serialization helper ──


def _serialize(obj: object) -> object:
    """Convert domain objects to JSON-serializable dicts.

    Handles Entity, Relationship, Alias, Schema, OrbitEntry, and any dataclass
    with a to_row() method. Recurses into lists and dicts.
    """
    if hasattr(obj, "to_row"):
        return obj.to_row()
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _print_json(data: object) -> None:
    """Pretty-print data as JSON to stdout."""
    print(json.dumps(_serialize(data), indent=2, ensure_ascii=False))


# ── Subcommand handlers ──


def cmd_stats(args: argparse.Namespace) -> None:
    """Print graph statistics: counts and resolution accuracy."""
    with OntoDB(args.db) as db:
        _print_json(db.stats())


def cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest unstructured text into the knowledge graph.

    Text is read from --text, --file, or stdin (if neither is provided).
    The LLM extracts entities and relationships, resolves them against
    existing graph data, and stores everything in the database.
    """
    if args.text:
        text = args.text
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print(
            "Error: provide text via --text, --file, or pipe to stdin.\n"
            "Example: echo 'Meeting notes...' | ontograph ingest",
            file=sys.stderr,
        )
        sys.exit(1)

    if not text.strip():
        print("Error: empty input text.", file=sys.stderr)
        sys.exit(1)

    with OntoDB(args.db) as db:
        result = db.ingest(
            text,
            source_type=args.source_type,
            schema_name=args.schema,
            observer_id=args.observer,
        )
        _print_json(result)


def cmd_search(args: argparse.Namespace) -> None:
    """Hybrid search: semantic + keyword + graph traversal.

    Combines three retrieval strategies to find the most relevant entities:
    1. Semantic similarity (embedding cosine distance)
    2. Keyword matching (FTS5 full-text search)
    3. Graph expansion (traverse relationships from top matches)

    Returns entities ranked by composite score with their relationships.
    """
    with OntoDB(args.db) as db:
        results = db.search(args.query, limit=args.limit, graph_depth=args.depth)
        _print_json(results)


def cmd_ask(args: argparse.Namespace) -> None:
    """Ask a natural language question and get an LLM-synthesized answer.

    Performs hybrid search to find relevant context in the knowledge graph,
    then passes that context to the LLM to generate a grounded answer.
    """
    with OntoDB(args.db) as db:
        if args.sources:
            result = db.ask_with_sources(
                args.question, limit=args.limit, graph_depth=args.depth
            )
            _print_json(result)
        else:
            answer = db.ask(args.question, limit=args.limit, graph_depth=args.depth)
            print(answer)


def cmd_entities(args: argparse.Namespace) -> None:
    """List all entities in the graph, optionally filtered by type."""
    with OntoDB(args.db) as db:
        entities = db.list_entities(entity_type=args.type)
        _print_json(entities)


def cmd_entity(args: argparse.Namespace) -> None:
    """Look up a single entity by name or ID."""
    with OntoDB(args.db) as db:
        entity = db.get_entity(args.name_or_id)
        if entity is None:
            print(
                json.dumps({"error": f"Entity not found: {args.name_or_id}"}),
                file=sys.stderr,
            )
            sys.exit(1)
        _print_json(entity)


def cmd_relationships(args: argparse.Namespace) -> None:
    """List relationships for a given entity (by name or ID).

    Optionally filter by relationship type or direction (incoming/outgoing).
    """
    with OntoDB(args.db) as db:
        rels = db.get_relationships(
            args.entity,
            relationship_type=args.type,
            direction=args.direction,
        )
        _print_json(rels)


def cmd_neighbors(args: argparse.Namespace) -> None:
    """Find entities connected to a given entity within N hops.

    Traverses the relationship graph outward from the specified entity,
    returning all reachable entities within the given depth.
    """
    with OntoDB(args.db) as db:
        neighbors = db.get_neighbors(args.entity, depth=args.depth)
        _print_json(neighbors)


def cmd_resolve(args: argparse.Namespace) -> None:
    """Resolve a name to an existing entity using composite scoring.

    Uses four signals for matching:
    1. Phonetic similarity (Metaphone)
    2. Spelling similarity (Jaro-Winkler)
    3. Semantic similarity (embedding cosine distance)
    4. Orbit proximity (interaction frequency with observer)

    Returns the best match and confidence score, or null if no match
    meets the threshold.
    """
    with OntoDB(args.db) as db:
        entity, score = db.resolve(
            args.name, entity_type=args.type, observer=args.observer
        )
        result = {
            "resolved_entity": _serialize(entity) if entity else None,
            "confidence": round(score, 4),
        }
        _print_json(result)


def cmd_orbit(args: argparse.Namespace) -> None:
    """Show the orbit (proximity-ranked entities) for an observer.

    Entities are ranked by time-decayed interaction frequency. Entities
    the observer interacts with more frequently and more recently appear
    higher in the orbit.
    """
    with OntoDB(args.db) as db:
        results = db.orbit(observer=args.observer, limit=args.limit)
        _print_json(results)


def cmd_add_entity(args: argparse.Namespace) -> None:
    """Manually add an entity to the knowledge graph.

    Generates an embedding for the entity and stores it in the database.
    Optionally attach key-value attributes and aliases.
    """
    attributes = {}
    if args.attributes:
        attributes = json.loads(args.attributes)

    aliases = None
    if args.aliases:
        aliases = json.loads(args.aliases)

    with OntoDB(args.db) as db:
        entity = db.add_entity(
            name=args.name,
            entity_type=args.type,
            attributes=attributes,
            aliases=aliases,
        )
        _print_json(entity)


def cmd_add_relationship(args: argparse.Namespace) -> None:
    """Manually add a relationship between two existing entities.

    Source and target can be entity names or IDs. Use --undirected for
    bidirectional relationships (e.g., 'colleague', 'sibling').
    """
    attributes = {}
    if args.attributes:
        attributes = json.loads(args.attributes)

    with OntoDB(args.db) as db:
        rel = db.add_relationship(
            source=args.source,
            target=args.target,
            relationship_type=args.type,
            directed=not args.undirected,
            attributes=attributes,
        )
        _print_json(rel)


def cmd_add_alias(args: argparse.Namespace) -> None:
    """Add an alternate name (alias) for an existing entity.

    Useful for handling nicknames, abbreviations, and transcription errors.
    The alias will be considered during entity resolution.
    """
    with OntoDB(args.db) as db:
        entity = db.get_entity(args.entity)
        if entity is None:
            print(
                json.dumps({"error": f"Entity not found: {args.entity}"}),
                file=sys.stderr,
            )
            sys.exit(1)
        alias = db.add_alias(entity.id, args.alias, alias_type=args.alias_type)
        _print_json(alias)


def cmd_schema_register(args: argparse.Namespace) -> None:
    """Register an ontology schema from a JSON definition.

    A schema constrains which entity types and relationship types the LLM
    can extract during ingestion, reducing hallucinated entities.

    The JSON must have this structure:
    {
        "name": "schema_name",
        "entity_types": ["person", "project", ...],
        "relationship_types": [
            {"name": "works_on", "directed": true},
            {"name": "colleague", "directed": false}
        ]
    }
    """
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(path.read_text())
    elif args.json:
        data = json.loads(args.json)
    elif not sys.stdin.isatty():
        data = json.loads(sys.stdin.read())
    else:
        print(
            "Error: provide schema JSON via --file, --json, or pipe to stdin.\n"
            'Example: ontograph schema register --json \'{"name":"work","entity_types":["person"],'
            '"relationship_types":[{"name":"works_on","directed":true}]}\'',
            file=sys.stderr,
        )
        sys.exit(1)

    schema = Schema(
        name=data["name"],
        entity_types=data["entity_types"],
        relationship_types=data["relationship_types"],
    )

    with OntoDB(args.db) as db:
        result = db.register_schema(schema)
        _print_json(result)


def cmd_schema_list(args: argparse.Namespace) -> None:
    """List all registered ontology schemas."""
    with OntoDB(args.db) as db:
        schemas = db.list_schemas()
        _print_json(schemas)


def cmd_schema_get(args: argparse.Namespace) -> None:
    """Get a specific schema by name."""
    with OntoDB(args.db) as db:
        schema = db.get_schema(args.name)
        if schema is None:
            print(
                json.dumps({"error": f"Schema not found: {args.name}"}),
                file=sys.stderr,
            )
            sys.exit(1)
        _print_json(schema)


# ── Parser construction ──


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands.

    Each subcommand has detailed help text and usage examples accessible
    via `ontograph <command> --help`.
    """
    parser = argparse.ArgumentParser(
        prog="ontograph",
        description=(
            "ontograph — LLM-powered knowledge graph engine.\n\n"
            "Build and query knowledge graphs from unstructured text using LLM-driven\n"
            "entity extraction, composite entity resolution, orbit-based proximity\n"
            "scoring, and hybrid semantic-graph retrieval.\n\n"
            "All output is JSON by default. Set OPENAI_API_KEY before using commands\n"
            "that call the LLM or embedding model."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  # Show graph statistics\n"
            "  ontograph stats\n\n"
            "  # Ingest a meeting transcript\n"
            '  ontograph ingest --text "Nara discussed Project Neptune with Marco."\n\n'
            "  # Ingest from a file\n"
            "  ontograph ingest --file meeting_notes.txt --source-type transcript\n\n"
            "  # Ingest from stdin (pipe-friendly for LLM tool use)\n"
            "  echo 'Meeting notes here...' | ontograph ingest\n\n"
            "  # Search the knowledge graph\n"
            '  ontograph search "Project Neptune"\n\n'
            "  # Ask a question and get an LLM-synthesized answer\n"
            '  ontograph ask "Who is working on Project Neptune?"\n\n'
            "  # List all person entities\n"
            "  ontograph entities --type person\n\n"
            "  # Register a schema to constrain extraction\n"
            "  ontograph schema register --file workplace_schema.json\n\n"
            "  # Use a specific database file\n"
            "  ontograph --db project.db stats\n\n"
            "  # Resolve a potentially ambiguous name\n"
            '  ontograph resolve "Sam" --type person\n'
        ),
    )

    parser.add_argument(
        "--version", action="version", version=f"ontograph {__version__}"
    )
    parser.add_argument(
        "--db",
        "-d",
        default="ontograph.db",
        metavar="PATH",
        help="Path to the SQLite database file. Created if missing. (default: ontograph.db)",
    )

    subparsers = parser.add_subparsers(dest="command", title="commands")

    # ── stats ──
    p_stats = subparsers.add_parser(
        "stats",
        help="Show graph statistics (entity, relationship, document, alias counts).",
        description=(
            "Display counts of all objects in the knowledge graph and resolution\n"
            "accuracy metrics from the entity resolution audit log."
        ),
        epilog=(
            "examples:\n"
            "  ontograph stats\n"
            "  ontograph stats --db project.db\n"
            "  ontograph stats | jq '.entities'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_stats.set_defaults(func=cmd_stats)

    # ── ingest ──
    p_ingest = subparsers.add_parser(
        "ingest",
        help="Ingest unstructured text into the knowledge graph.",
        description=(
            "Feed unstructured text to the LLM for entity and relationship extraction.\n"
            "Extracted entities are resolved against the existing graph to prevent\n"
            "duplicates. New entities get embeddings for semantic search.\n\n"
            "Text can come from three sources (checked in this order):\n"
            "  1. --text 'inline string'\n"
            "  2. --file path/to/document.txt\n"
            "  3. stdin (pipe or redirect)\n\n"
            "Requires OPENAI_API_KEY."
        ),
        epilog=(
            "examples:\n"
            '  # Inline text\n'
            '  ontograph ingest --text "Nara met Marco to discuss the product roadmap."\n\n'
            "  # From a file with source type\n"
            "  ontograph ingest --file transcript.txt --source-type transcript\n\n"
            "  # From stdin (great for piping from other tools or LLM tool use)\n"
            "  cat meeting.txt | ontograph ingest --source-type transcript\n\n"
            "  # With a schema to constrain extraction\n"
            "  ontograph ingest --file notes.txt --schema workplace\n\n"
            "  # With orbit tracking for a specific observer\n"
            "  ontograph ingest --file notes.txt --observer abc123def456\n\n"
            "  # Chain: ingest then check stats\n"
            '  ontograph ingest --text "Lena works on Project Orion." && ontograph stats\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_ingest.add_argument(
        "--text",
        "-t",
        metavar="TEXT",
        help="Text to ingest (inline). Mutually exclusive with --file and stdin.",
    )
    p_ingest.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        help="Path to a text file to ingest.",
    )
    p_ingest.add_argument(
        "--source-type",
        "-s",
        default="text",
        metavar="TYPE",
        help="Source type label (e.g., transcript, brief, note, email). (default: text)",
    )
    p_ingest.add_argument(
        "--schema",
        metavar="NAME",
        help="Name of a registered ontology schema to constrain extraction.",
    )
    p_ingest.add_argument(
        "--observer",
        metavar="ID",
        help="Observer entity ID for orbit proximity tracking.",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    # ── search ──
    p_search = subparsers.add_parser(
        "search",
        help="Hybrid search: semantic + keyword + graph traversal.",
        description=(
            "Search the knowledge graph using three combined strategies:\n\n"
            "  1. Semantic: embed the query and find nearest entities by cosine similarity\n"
            "  2. Keyword: FTS5 full-text search over entity names and types\n"
            "  3. Graph: traverse relationships from top matches to find connected context\n\n"
            "Results are ranked by a composite score. Each result includes the matched\n"
            "entity, its score, how it was found (semantic/keyword/graph), and its\n"
            "relationships.\n\n"
            "Requires OPENAI_API_KEY."
        ),
        epilog=(
            "examples:\n"
            '  ontograph search "Project Neptune"\n'
            '  ontograph search "who works with Nara" --limit 5\n'
            '  ontograph search "machine learning" --depth 2 --limit 20\n'
            '  ontograph search "product roadmap" | jq \'.[0].entity\'\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_search.add_argument("query", help="Natural language search query.")
    p_search.add_argument(
        "--limit",
        "-n",
        type=int,
        default=10,
        metavar="N",
        help="Maximum number of results to return. (default: 10)",
    )
    p_search.add_argument(
        "--depth",
        type=int,
        default=1,
        metavar="N",
        help="Graph traversal depth for expanding results. (default: 1)",
    )
    p_search.set_defaults(func=cmd_search)

    # ── ask ──
    p_ask = subparsers.add_parser(
        "ask",
        help="Ask a question and get an LLM-synthesized answer from the graph.",
        description=(
            "Performs hybrid search to find relevant context in the knowledge graph,\n"
            "then passes that context to the LLM to generate a grounded, natural\n"
            "language answer.\n\n"
            "By default, prints just the answer text. Use --sources to get the full\n"
            "JSON response including the source entities and relationships used.\n\n"
            "Requires OPENAI_API_KEY."
        ),
        epilog=(
            "examples:\n"
            '  ontograph ask "Who is working on Project Neptune?"\n'
            '  ontograph ask "What topics were discussed in the last meeting?" --sources\n'
            '  ontograph ask "How is Marco connected to the remote office?" --depth 2\n'
            '  ontograph ask "Summarize all known projects" --limit 20 --sources | jq .answer\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_ask.add_argument("question", help="Natural language question.")
    p_ask.add_argument(
        "--sources",
        action="store_true",
        help="Include source entities and relationships in the output (JSON).",
    )
    p_ask.add_argument(
        "--limit",
        "-n",
        type=int,
        default=10,
        metavar="N",
        help="Maximum number of search results for context. (default: 10)",
    )
    p_ask.add_argument(
        "--depth",
        type=int,
        default=1,
        metavar="N",
        help="Graph traversal depth for context expansion. (default: 1)",
    )
    p_ask.set_defaults(func=cmd_ask)

    # ── entities ──
    p_entities = subparsers.add_parser(
        "entities",
        help="List all entities in the graph.",
        description=(
            "List every entity stored in the knowledge graph. Optionally filter\n"
            "by entity type (e.g., person, project, topic)."
        ),
        epilog=(
            "examples:\n"
            "  ontograph entities\n"
            "  ontograph entities --type person\n"
            "  ontograph entities --type project | jq '.[].name'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_entities.add_argument(
        "--type",
        metavar="TYPE",
        help="Filter entities by type (e.g., person, project, topic).",
    )
    p_entities.set_defaults(func=cmd_entities)

    # ── entity ──
    p_entity = subparsers.add_parser(
        "entity",
        help="Get a single entity by name or ID.",
        description=(
            "Look up a specific entity by its name or 12-character hex ID.\n"
            "Searches by ID first, then falls back to case-insensitive name match."
        ),
        epilog=(
            "examples:\n"
            '  ontograph entity "Nara Kim"\n'
            "  ontograph entity abc123def456\n"
            '  ontograph entity "Project Neptune" | jq .attributes\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_entity.add_argument(
        "name_or_id", help="Entity name (case-insensitive) or 12-char hex ID."
    )
    p_entity.set_defaults(func=cmd_entity)

    # ── relationships ──
    p_rels = subparsers.add_parser(
        "relationships",
        help="List relationships for an entity.",
        description=(
            "Show all relationships involving a given entity. Optionally filter\n"
            "by relationship type or direction.\n\n"
            "Directions:\n"
            "  outgoing  — entity is the source\n"
            "  incoming  — entity is the target\n"
            "  (default) — both directions"
        ),
        epilog=(
            "examples:\n"
            '  ontograph relationships "Nara Kim"\n'
            '  ontograph relationships "Nara Kim" --type works_on\n'
            '  ontograph relationships "Project Neptune" --direction incoming\n'
            '  ontograph relationships abc123def456 --type colleague --direction outgoing\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_rels.add_argument(
        "entity", help="Entity name or ID to find relationships for."
    )
    p_rels.add_argument(
        "--type",
        metavar="TYPE",
        help="Filter by relationship type (e.g., works_on, colleague).",
    )
    p_rels.add_argument(
        "--direction",
        choices=["incoming", "outgoing"],
        help="Filter by direction: incoming (entity is target) or outgoing (entity is source).",
    )
    p_rels.set_defaults(func=cmd_relationships)

    # ── neighbors ──
    p_neighbors = subparsers.add_parser(
        "neighbors",
        help="Find entities connected within N hops.",
        description=(
            "Traverse the relationship graph outward from a given entity and\n"
            "return all reachable entities within the specified depth.\n\n"
            "Depth 1 returns directly connected entities. Depth 2 includes\n"
            "entities connected through one intermediary, and so on."
        ),
        epilog=(
            "examples:\n"
            '  ontograph neighbors "Nara Kim"\n'
            '  ontograph neighbors "Project Neptune" --depth 2\n'
            '  ontograph neighbors abc123def456 --depth 3 | jq \'.[].name\'\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_neighbors.add_argument("entity", help="Entity name or ID to start from.")
    p_neighbors.add_argument(
        "--depth",
        type=int,
        default=1,
        metavar="N",
        help="Maximum traversal depth (number of hops). (default: 1)",
    )
    p_neighbors.set_defaults(func=cmd_neighbors)

    # ── resolve ──
    p_resolve = subparsers.add_parser(
        "resolve",
        help="Resolve an ambiguous name to an existing entity.",
        description=(
            "Attempt to match a name to an existing entity using four-signal\n"
            "composite scoring:\n\n"
            "  1. Phonetic similarity (Metaphone) — catches 'Nara' vs 'Narah'\n"
            "  2. Spelling similarity (Jaro-Winkler) — catches 'Nraa' vs 'Nara'\n"
            "  3. Semantic similarity (embedding distance) — catches 'JFK' vs 'Kennedy'\n"
            "  4. Orbit proximity (interaction frequency) — prioritizes entities\n"
            "     the observer interacts with frequently\n\n"
            "Returns the best matching entity and a confidence score (0-1).\n"
            "Returns null if no match exceeds the resolution threshold.\n\n"
            "Requires OPENAI_API_KEY."
        ),
        epilog=(
            "examples:\n"
            '  ontograph resolve "Sam"\n'
            '  ontograph resolve "Nara" --type person\n'
            '  ontograph resolve "Prjct Neptune" --observer abc123def456\n'
            '  ontograph resolve "N. Kim" | jq .confidence\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_resolve.add_argument(
        "name", help="Name to resolve against the existing entity graph."
    )
    p_resolve.add_argument(
        "--type",
        metavar="TYPE",
        help="Expected entity type to narrow resolution candidates.",
    )
    p_resolve.add_argument(
        "--observer",
        metavar="ID",
        help="Observer entity ID for orbit-weighted resolution.",
    )
    p_resolve.set_defaults(func=cmd_resolve)

    # ── orbit ──
    p_orbit = subparsers.add_parser(
        "orbit",
        help="Show proximity-ranked entities for an observer.",
        description=(
            "Display the orbit for a given observer entity — a list of entities\n"
            "ranked by time-decayed interaction frequency.\n\n"
            "Entities the observer interacts with more frequently and more recently\n"
            "appear higher in the orbit. This drives context-aware entity resolution:\n"
            "when resolving 'Sam', the observer's manager 'Sam Owens' ranks above a\n"
            "distant 'Sal Ortega' because Sam Owens is in their orbit."
        ),
        epilog=(
            "examples:\n"
            "  ontograph orbit --observer abc123def456\n"
            "  ontograph orbit --observer abc123def456 --limit 10\n"
            "  ontograph orbit --observer abc123def456 | jq '.[].entity.name'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_orbit.add_argument(
        "--observer",
        required=True,
        metavar="ID",
        help="Observer entity name or ID.",
    )
    p_orbit.add_argument(
        "--limit",
        "-n",
        type=int,
        default=50,
        metavar="N",
        help="Maximum number of orbit entries to return. (default: 50)",
    )
    p_orbit.set_defaults(func=cmd_orbit)

    # ── add-entity ──
    p_add_entity = subparsers.add_parser(
        "add-entity",
        help="Manually add an entity to the graph.",
        description=(
            "Create a new entity node in the knowledge graph. The entity gets\n"
            "an embedding generated from its name and type for semantic search.\n\n"
            "Requires OPENAI_API_KEY."
        ),
        epilog=(
            "examples:\n"
            '  ontograph add-entity "Nara Kim" --type person\n\n'
            "  # With attributes\n"
            '  ontograph add-entity "Project Neptune" --type project \\\n'
            "    --attributes '{\"status\": \"active\", \"team\": \"engineering\"}'\n\n"
            "  # With aliases (for entity resolution)\n"
            '  ontograph add-entity "Nara Kim" --type person \\\n'
            '    --aliases \'[{"alias": "Nar", "type": "nickname"}, '
            '{"alias": "N. Kim", "type": "abbreviation"}]\'\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_add_entity.add_argument("name", help="Entity name.")
    p_add_entity.add_argument(
        "--type",
        required=True,
        metavar="TYPE",
        help="Entity type (e.g., person, project, topic, organization).",
    )
    p_add_entity.add_argument(
        "--attributes",
        metavar="JSON",
        help='Key-value attributes as a JSON object. Example: \'{"role": "engineer"}\'',
    )
    p_add_entity.add_argument(
        "--aliases",
        metavar="JSON",
        help=(
            "Aliases as a JSON array. Each item: "
            '{\"alias\": \"name\", \"type\": \"nickname|abbreviation|transcript_error\"}.'
        ),
    )
    p_add_entity.set_defaults(func=cmd_add_entity)

    # ── add-relationship ──
    p_add_rel = subparsers.add_parser(
        "add-relationship",
        help="Manually add a relationship between two entities.",
        description=(
            "Create a directed or bidirectional edge between two existing entities.\n"
            "Source and target can be entity names or IDs."
        ),
        epilog=(
            "examples:\n"
            "  # Directed relationship (default)\n"
            '  ontograph add-relationship "Nara Kim" "Project Neptune" --type works_on\n\n'
            "  # Bidirectional relationship\n"
            '  ontograph add-relationship "Nara" "Marco" --type colleague --undirected\n\n'
            "  # With attributes\n"
            '  ontograph add-relationship "Nara" "Project Neptune" --type works_on \\\n'
            "    --attributes '{\"role\": \"lead\", \"since\": \"2025-01\"}'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_add_rel.add_argument("source", help="Source entity name or ID.")
    p_add_rel.add_argument("target", help="Target entity name or ID.")
    p_add_rel.add_argument(
        "--type",
        required=True,
        metavar="TYPE",
        help="Relationship type (e.g., works_on, colleague, reports_to).",
    )
    p_add_rel.add_argument(
        "--undirected",
        action="store_true",
        help="Make the relationship bidirectional. (default: directed)",
    )
    p_add_rel.add_argument(
        "--attributes",
        metavar="JSON",
        help='Key-value attributes as a JSON object. Example: \'{"since": "2025-01"}\'',
    )
    p_add_rel.set_defaults(func=cmd_add_relationship)

    # ── add-alias ──
    p_add_alias = subparsers.add_parser(
        "add-alias",
        help="Add an alternate name for an entity.",
        description=(
            "Register an alias (alternate name) for an existing entity. Aliases\n"
            "are used during entity resolution to match different spellings,\n"
            "nicknames, abbreviations, or known transcription errors.\n\n"
            "Alias types:\n"
            "  alternate          — general alternate name\n"
            "  nickname           — informal name (e.g., 'Nar' for 'Nara')\n"
            "  abbreviation       — shortened form (e.g., 'N. Kim')\n"
            "  transcript_error   — known ASR/transcription mistake"
        ),
        epilog=(
            "examples:\n"
            '  ontograph add-alias "Nara Kim" "Nar" --alias-type nickname\n'
            '  ontograph add-alias abc123def456 "N. Kim" --alias-type abbreviation\n'
            '  ontograph add-alias "Nara Kim" "Nara Kimm" --alias-type transcript_error\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_add_alias.add_argument("entity", help="Entity name or ID to add the alias to.")
    p_add_alias.add_argument("alias", help="The alternate name to register.")
    p_add_alias.add_argument(
        "--alias-type",
        default="alternate",
        metavar="TYPE",
        help="Type: alternate, nickname, abbreviation, transcript_error. (default: alternate)",
    )
    p_add_alias.set_defaults(func=cmd_add_alias)

    # ── schema (subgroup) ──
    p_schema = subparsers.add_parser(
        "schema",
        help="Manage ontology schemas (register, list, get).",
        description=(
            "Ontology schemas define the vocabulary of valid entity types and\n"
            "relationship types for a domain. When a schema is specified during\n"
            "ingestion, the LLM is constrained to extract only entities and\n"
            "relationships matching the schema's types."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    schema_sub = p_schema.add_subparsers(dest="schema_command", title="schema commands")

    # ── schema register ──
    p_schema_reg = schema_sub.add_parser(
        "register",
        help="Register a new ontology schema.",
        description=(
            "Register an ontology schema from a JSON definition. The schema\n"
            "constrains LLM extraction during ingestion.\n\n"
            "JSON input can come from three sources (checked in this order):\n"
            "  1. --json 'inline JSON string'\n"
            "  2. --file path/to/schema.json\n"
            "  3. stdin"
        ),
        epilog=(
            "examples:\n"
            "  # From a file\n"
            "  ontograph schema register --file workplace_schema.json\n\n"
            "  # Inline JSON\n"
            "  ontograph schema register --json '{\n"
            '    "name": "workplace",\n'
            '    "entity_types": ["person", "project", "team", "organization"],\n'
            '    "relationship_types": [\n'
            '      {"name": "works_on", "directed": true},\n'
            '      {"name": "manages", "directed": true},\n'
            '      {"name": "colleague", "directed": false}\n'
            "    ]\n"
            "  }'\n\n"
            "  # From stdin\n"
            "  cat schema.json | ontograph schema register\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_schema_reg.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        help="Path to a JSON file containing the schema definition.",
    )
    p_schema_reg.add_argument(
        "--json",
        "-j",
        metavar="JSON",
        help="Inline JSON schema definition string.",
    )
    p_schema_reg.set_defaults(func=cmd_schema_register)

    # ── schema list ──
    p_schema_list = schema_sub.add_parser(
        "list",
        help="List all registered schemas.",
        epilog=(
            "examples:\n"
            "  ontograph schema list\n"
            "  ontograph schema list | jq '.[].name'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_schema_list.set_defaults(func=cmd_schema_list)

    # ── schema get ──
    p_schema_get = schema_sub.add_parser(
        "get",
        help="Get a specific schema by name.",
        epilog=(
            "examples:\n"
            "  ontograph schema get workplace\n"
            "  ontograph schema get workplace | jq .entity_types\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_schema_get.add_argument("name", help="Schema name to look up.")
    p_schema_get.set_defaults(func=cmd_schema_get)

    return parser


def main() -> None:
    """Entry point for the ontograph CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Handle 'schema' subgroup without a sub-subcommand
    if args.command == "schema" and not hasattr(args, "func"):
        parser.parse_args(["schema", "--help"])
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
