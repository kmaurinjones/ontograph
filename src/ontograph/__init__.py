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

__all__ = [
    "OntoDB",
    "Entity",
    "Relationship",
    "Alias",
    "Schema",
    "OrbitEntry",
    "set_llm_provider",
]

__version__ = "0.4.0"
