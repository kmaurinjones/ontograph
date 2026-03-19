"""ontograph: LLM-powered knowledge graph with ontological entity resolution.

Usage:
    from ontograph import OntoDB, Schema

    db = OntoDB("my_knowledge.db")
    db.ingest("Meeting transcript text here...", source_type="transcript")
    results = db.search("What did we discuss?")
    answer = db.ask("Who is working on Project Neptune?")
"""

from ontograph.config import set_llm_provider
from ontograph.models import Alias, Entity, OrbitEntry, Relationship, Schema
from ontograph.onto import OntoDB
from ontograph.schema_registry import EXPANDED_SCHEMA
from ontograph.temporal import normalize_temporal

__all__ = [
    "OntoDB",
    "Entity",
    "Relationship",
    "Alias",
    "Schema",
    "OrbitEntry",
    "set_llm_provider",
    "EXPANDED_SCHEMA",
    "normalize_temporal",
]

__version__ = "0.5.0"
