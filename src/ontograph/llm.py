"""OpenAI LLM and embedding clients.

Uses the Responses API for all LLM calls and text-embedding-3-small for embeddings.
Default model: gpt-4o-mini (cost-efficient for high-volume operations).
"""

from __future__ import annotations

import json

import numpy as np
from openai import OpenAI

from ontograph.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, LLM_MODEL, get_api_key

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_api_key())
    return _client


def set_client(client: OpenAI) -> None:
    """Override the default OpenAI client (useful for testing or custom configs)."""
    global _client
    _client = client


def embed(text: str) -> list[float]:
    """Embed a single text string using text-embedding-3-small."""
    client = _get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single API call."""
    if not texts:
        return []
    client = _get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    sorted_data = sorted(response.data, key=lambda d: d.index)
    return [d.embedding for d in sorted_data]


def cosine_similarity(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    dot = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def llm_call(prompt: str, system: str | None = None, model: str = LLM_MODEL) -> str:
    """Make an LLM call via the OpenAI Responses API.

    Returns the raw text output from the model.
    """
    client = _get_client()
    instructions = system or "You are a precise knowledge extraction assistant."
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=prompt,
    )
    return response.output_text


def llm_call_json(
    prompt: str, system: str | None = None, model: str = LLM_MODEL
) -> dict | list:
    """Make an LLM call and parse the response as JSON.

    The prompt should instruct the model to return valid JSON.
    """
    raw = llm_call(prompt, system=system, model=model)

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    return json.loads(cleaned)
