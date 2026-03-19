"""LLM and embedding clients for ontograph.

Supports two LLM providers:
- OpenAI (default): Responses API with gpt-4o-mini
- Google Gemini: google-genai SDK with gemini-2.5-flash-lite

Embeddings always use OpenAI text-embedding-3-small (256-dim).

Provider and model selection is controlled by config (see config.py).
"""

from __future__ import annotations

import json

import numpy as np
from openai import OpenAI

from ontograph.config import (
    get_api_key,
    get_embedding_dimensions,
    get_embedding_model,
    get_google_api_key,
    get_llm_model,
    get_llm_provider,
)

# ── OpenAI client ──

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


# ── Google Gemini client ──

_google_client = None


def _get_google_client():
    """Lazy-init the Google genai client."""
    global _google_client
    if _google_client is None:
        from google import genai

        _google_client = genai.Client(api_key=get_google_api_key())
    return _google_client


# ── Embeddings (always OpenAI) ──


def embed(text: str) -> list[float]:
    """Embed a single text string using the configured embedding model."""
    client = _get_client()
    response = client.embeddings.create(
        model=get_embedding_model(),
        input=text,
        dimensions=get_embedding_dimensions(),
    )
    return response.data[0].embedding


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single API call."""
    if not texts:
        return []
    client = _get_client()
    response = client.embeddings.create(
        model=get_embedding_model(),
        input=texts,
        dimensions=get_embedding_dimensions(),
    )
    sorted_data = sorted(response.data, key=lambda d: d.index)
    return [d.embedding for d in sorted_data]


# ── Similarity ──


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


# ── LLM calls (provider-dispatched) ──


def _openai_llm_call(prompt: str, system: str | None = None, model: str | None = None) -> str:
    """LLM call via the OpenAI Responses API."""
    client = _get_client()
    instructions = system or "You are a precise knowledge extraction assistant."
    response = client.responses.create(
        model=model or get_llm_model(),
        instructions=instructions,
        input=prompt,
    )
    return response.output_text


def _google_llm_call(prompt: str, system: str | None = None, model: str | None = None) -> str:
    """LLM call via the Google Gemini SDK."""
    from google.genai import types

    client = _get_google_client()
    instructions = system or "You are a precise knowledge extraction assistant."

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]
    config = types.GenerateContentConfig(
        system_instruction=instructions,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    response = client.models.generate_content(
        model=model or get_llm_model(),
        contents=contents,
        config=config,
    )
    return response.text


def llm_call(prompt: str, system: str | None = None, model: str | None = None) -> str:
    """Make an LLM call using the configured provider.

    Routes to OpenAI or Google Gemini based on the current provider setting.
    Returns the raw text output from the model.
    """
    provider = get_llm_provider()
    if provider == "google":
        return _google_llm_call(prompt, system=system, model=model)
    return _openai_llm_call(prompt, system=system, model=model)


def llm_call_json(
    prompt: str, system: str | None = None, model: str | None = None
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
