"""Configuration for ontograph. Requires OPENAI_API_KEY environment variable.

Automatically loads .env from the current working directory (via python-dotenv)
so users can set OPENAI_API_KEY in a .env file instead of exporting it.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def get_api_key() -> str:
    """Return the OpenAI API key from environment. Fails hard if missing."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable is required. "
            "Set it in a .env file or export it: export OPENAI_API_KEY='sk-...'"
        )
    return key


# Model defaults — do NOT modify these values
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 256
LLM_MODEL = "gpt-4o-mini"

# Entity resolution thresholds
RESOLUTION_THRESHOLD = 0.72
ORBIT_DECAY_FACTOR = 0.95
