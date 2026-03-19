"""Configuration for ontograph.

Loads configuration from multiple sources with this precedence (highest wins):
1. Runtime overrides (constructor kwargs / set_* calls)
2. Environment variables (ONTOGRAPH_LLM_PROVIDER, ONTOGRAPH_LLM_MODEL, etc.)
3. Project-level config: .ontograph/config.yaml (in working directory)
4. User-level config: ~/.ontograph/config.yaml
5. Hardcoded defaults

Config file format (YAML):
    llm:
      provider: google          # openai | google
      model: gemini-2.5-flash-lite

    embeddings:
      provider: openai          # openai (only option today)
      model: text-embedding-3-small
      dimensions: 256

API keys are NOT stored in config files — use .env or env vars:
    OPENAI_API_KEY, GEMINI_API_KEY
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

# ── Hardcoded defaults ──

_VALID_LLM_PROVIDERS = ("openai", "google")

_PROVIDER_DEFAULT_LLM_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "google": "gemini-2.5-flash-lite",
}

_DEFAULTS: dict[str, dict[str, str | int]] = {
    "llm": {
        "provider": "openai",
    },
    "embeddings": {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "dimensions": 256,
    },
}

# ── Environment variable mapping ──

_ENV_MAP: dict[tuple[str, str], str] = {
    ("llm", "provider"): "ONTOGRAPH_LLM_PROVIDER",
    ("llm", "model"): "ONTOGRAPH_LLM_MODEL",
    ("embeddings", "provider"): "ONTOGRAPH_EMBEDDINGS_PROVIDER",
    ("embeddings", "model"): "ONTOGRAPH_EMBEDDINGS_MODEL",
    ("embeddings", "dimensions"): "ONTOGRAPH_EMBEDDINGS_DIMENSIONS",
}

# ── Runtime overrides (set by constructor kwargs / set_* calls) ──

_runtime: dict[str, dict[str, str | int]] = {}

# ── Config file cache ──

_user_config: dict | None = None
_project_config: dict | None = None
_configs_loaded: bool = False


def _load_yaml_file(path: Path) -> dict:
    """Load a YAML file, returning empty dict if it doesn't exist or is empty."""
    if not path.is_file():
        return {}
    text = path.read_text().strip()
    if not text:
        return {}
    parsed = yaml.safe_load(text)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _load_configs() -> None:
    """Load user-level and project-level config files (cached after first call)."""
    global _user_config, _project_config, _configs_loaded
    if _configs_loaded:
        return

    _user_config = _load_yaml_file(Path.home() / ".ontograph" / "config.yaml")
    _project_config = _load_yaml_file(Path.cwd() / ".ontograph" / "config.yaml")
    _configs_loaded = True


def reload_configs() -> None:
    """Force reload of config files from disk. Useful after modifying config files."""
    global _configs_loaded
    _configs_loaded = False
    _load_configs()


def _resolve(section: str, key: str) -> str | int | None:
    """Resolve a config value through the full precedence chain.

    Order: runtime > env var > project config > user config > defaults.
    Returns None if not found at any level.
    """
    # 1. Runtime overrides
    if section in _runtime and key in _runtime[section]:
        return _runtime[section][key]

    # 2. Environment variables
    env_key = _ENV_MAP.get((section, key))
    if env_key:
        env_val = os.environ.get(env_key)
        if env_val is not None:
            # Coerce dimensions to int
            if key == "dimensions":
                return int(env_val)
            return env_val

    # 3. Project-level config
    _load_configs()
    assert _project_config is not None
    if section in _project_config and key in _project_config[section]:
        return _project_config[section][key]

    # 4. User-level config
    assert _user_config is not None
    if section in _user_config and key in _user_config[section]:
        return _user_config[section][key]

    # 5. Hardcoded defaults
    if section in _DEFAULTS and key in _DEFAULTS[section]:
        return _DEFAULTS[section][key]

    return None


# ── Public setters (runtime overrides) ──


def set_llm_provider(provider: str) -> None:
    """Set the LLM provider at runtime. Valid values: 'openai', 'google'."""
    if provider not in _VALID_LLM_PROVIDERS:
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. Must be one of {_VALID_LLM_PROVIDERS}."
        )
    _runtime.setdefault("llm", {})["provider"] = provider


def set_llm_model(model: str) -> None:
    """Override the LLM model at runtime."""
    _runtime.setdefault("llm", {})["model"] = model


def set_embedding_model(model: str) -> None:
    """Override the embedding model at runtime."""
    _runtime.setdefault("embeddings", {})["model"] = model


def set_embedding_dimensions(dimensions: int) -> None:
    """Override embedding dimensions at runtime."""
    _runtime.setdefault("embeddings", {})["dimensions"] = dimensions


def clear_runtime_overrides() -> None:
    """Clear all runtime overrides. Useful for testing."""
    _runtime.clear()


# ── Public getters ──


def get_llm_provider() -> str:
    """Return the LLM provider ('openai' or 'google')."""
    value = _resolve("llm", "provider")
    assert value is not None
    provider = str(value)
    if provider not in _VALID_LLM_PROVIDERS:
        raise ValueError(
            f"Invalid LLM provider in config: {provider!r}. "
            f"Must be one of {_VALID_LLM_PROVIDERS}."
        )
    return provider


def get_llm_model() -> str:
    """Return the LLM model name. Falls back to provider-specific default."""
    model = _resolve("llm", "model")
    if model is not None:
        return str(model)
    return _PROVIDER_DEFAULT_LLM_MODELS[get_llm_provider()]


def get_embedding_model() -> str:
    """Return the embedding model name."""
    value = _resolve("embeddings", "model")
    assert value is not None
    return str(value)


def get_embedding_dimensions() -> int:
    """Return the embedding dimensions."""
    value = _resolve("embeddings", "dimensions")
    assert value is not None
    return int(value)


# ── API keys (always from env vars / .env — never from config files) ──


def get_api_key() -> str:
    """Return the OpenAI API key from environment. Fails hard if missing."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable is required. "
            "Set it in a .env file or export it: export OPENAI_API_KEY='sk-...'"
        )
    return key


def get_google_api_key() -> str:
    """Return the Google/Gemini API key from environment. Fails hard if missing."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is required when using the Google LLM provider. "
            "Set it in a .env file or export it: export GEMINI_API_KEY='...'"
        )
    return key


# ── Backwards-compatible constants (for non-provider-specific code) ──
# These are used by orbit.py, resolve.py, etc. and are not provider-dependent.

RESOLUTION_THRESHOLD = 0.72
ORBIT_DECAY_FACTOR = 0.95


# ── Config file paths (for external tooling / diagnostics) ──


def user_config_path() -> Path:
    """Return the path to the user-level config file."""
    return Path.home() / ".ontograph" / "config.yaml"


def project_config_path() -> Path:
    """Return the path to the project-level config file (in cwd)."""
    return Path.cwd() / ".ontograph" / "config.yaml"
