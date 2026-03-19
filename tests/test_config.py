"""Tests for the config module — precedence chain, YAML loading, getters/setters."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from ontograph.config import (
    _load_yaml_file,
    clear_runtime_overrides,
    get_embedding_dimensions,
    get_embedding_model,
    get_llm_model,
    get_llm_provider,
    reload_configs,
    set_embedding_dimensions,
    set_embedding_model,
    set_llm_model,
    set_llm_provider,
)


@pytest.fixture(autouse=True)
def _clean_config_state():
    """Reset config state before each test."""
    clear_runtime_overrides()
    # Point config files at nonexistent paths so disk state doesn't leak in
    with patch("ontograph.config._user_config", {}), patch(
        "ontograph.config._project_config", {}
    ), patch("ontograph.config._configs_loaded", True):
        yield
    clear_runtime_overrides()


# ── Defaults ──


class TestDefaults:
    def test_default_llm_provider(self) -> None:
        assert get_llm_provider() == "openai"

    def test_default_llm_model(self) -> None:
        assert get_llm_model() == "gpt-4o-mini"

    def test_default_embedding_model(self) -> None:
        assert get_embedding_model() == "text-embedding-3-small"

    def test_default_embedding_dimensions(self) -> None:
        assert get_embedding_dimensions() == 256


# ── Runtime overrides ──


class TestRuntimeOverrides:
    def test_set_llm_provider(self) -> None:
        set_llm_provider("google")
        assert get_llm_provider() == "google"

    def test_set_llm_provider_changes_default_model(self) -> None:
        set_llm_provider("google")
        assert get_llm_model() == "gemini-2.5-flash-lite"

    def test_set_llm_model(self) -> None:
        set_llm_model("gpt-4o")
        assert get_llm_model() == "gpt-4o"

    def test_set_embedding_model(self) -> None:
        set_embedding_model("text-embedding-3-large")
        assert get_embedding_model() == "text-embedding-3-large"

    def test_set_embedding_dimensions(self) -> None:
        set_embedding_dimensions(1024)
        assert get_embedding_dimensions() == 1024

    def test_invalid_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            set_llm_provider("anthropic")

    def test_clear_overrides(self) -> None:
        set_llm_provider("google")
        set_llm_model("custom-model")
        clear_runtime_overrides()
        assert get_llm_provider() == "openai"
        assert get_llm_model() == "gpt-4o-mini"


# ── Environment variable precedence ──


class TestEnvVarPrecedence:
    def test_env_overrides_default(self) -> None:
        with patch.dict("os.environ", {"ONTOGRAPH_LLM_PROVIDER": "google"}):
            assert get_llm_provider() == "google"

    def test_env_overrides_model(self) -> None:
        with patch.dict("os.environ", {"ONTOGRAPH_LLM_MODEL": "gpt-4o"}):
            assert get_llm_model() == "gpt-4o"

    def test_env_overrides_embedding_dimensions(self) -> None:
        with patch.dict("os.environ", {"ONTOGRAPH_EMBEDDINGS_DIMENSIONS": "512"}):
            assert get_embedding_dimensions() == 512

    def test_runtime_beats_env(self) -> None:
        set_llm_provider("google")
        with patch.dict("os.environ", {"ONTOGRAPH_LLM_PROVIDER": "openai"}):
            assert get_llm_provider() == "google"


# ── YAML file loading ──


class TestYamlLoading:
    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        result = _load_yaml_file(tmp_path / "nope.yaml")
        assert result == {}

    def test_load_empty_file(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        assert _load_yaml_file(empty) == {}

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"llm": {"provider": "google"}}))
        result = _load_yaml_file(cfg)
        assert result["llm"]["provider"] == "google"

    def test_load_non_dict_yaml(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("just a string")
        assert _load_yaml_file(cfg) == {}


# ── Config file precedence ──


class TestConfigFilePrecedence:
    def test_user_config_overrides_default(self) -> None:
        with patch("ontograph.config._user_config", {"llm": {"provider": "google"}}), patch(
            "ontograph.config._project_config", {}
        ), patch("ontograph.config._configs_loaded", True):
            assert get_llm_provider() == "google"

    def test_project_config_overrides_user(self) -> None:
        with patch(
            "ontograph.config._user_config", {"llm": {"model": "user-model"}}
        ), patch(
            "ontograph.config._project_config", {"llm": {"model": "project-model"}}
        ), patch("ontograph.config._configs_loaded", True):
            assert get_llm_model() == "project-model"

    def test_env_overrides_project_config(self) -> None:
        with patch(
            "ontograph.config._project_config", {"llm": {"provider": "google"}}
        ), patch("ontograph.config._configs_loaded", True), patch.dict(
            "os.environ", {"ONTOGRAPH_LLM_PROVIDER": "openai"}
        ):
            assert get_llm_provider() == "openai"

    def test_runtime_overrides_everything(self) -> None:
        set_llm_model("runtime-model")
        with patch(
            "ontograph.config._user_config", {"llm": {"model": "user-model"}}
        ), patch(
            "ontograph.config._project_config", {"llm": {"model": "project-model"}}
        ), patch("ontograph.config._configs_loaded", True), patch.dict(
            "os.environ", {"ONTOGRAPH_LLM_MODEL": "env-model"}
        ):
            assert get_llm_model() == "runtime-model"


# ── Full precedence integration test ──


class TestFullPrecedence:
    def test_full_chain_llm_provider(self) -> None:
        """Each layer overrides the one below it."""
        # Default
        assert get_llm_provider() == "openai"

        # User config
        with patch(
            "ontograph.config._user_config", {"llm": {"provider": "google"}}
        ), patch("ontograph.config._project_config", {}), patch(
            "ontograph.config._configs_loaded", True
        ):
            assert get_llm_provider() == "google"

            # Project config overrides user
            with patch(
                "ontograph.config._project_config", {"llm": {"provider": "openai"}}
            ):
                assert get_llm_provider() == "openai"

                # Env var overrides project
                with patch.dict("os.environ", {"ONTOGRAPH_LLM_PROVIDER": "google"}):
                    assert get_llm_provider() == "google"

                    # Runtime overrides env
                    set_llm_provider("openai")
                    assert get_llm_provider() == "openai"

    def test_model_falls_back_to_provider_default(self) -> None:
        """When no model is explicitly set, it uses the provider's default."""
        with patch(
            "ontograph.config._user_config", {"llm": {"provider": "google"}}
        ), patch("ontograph.config._project_config", {}), patch(
            "ontograph.config._configs_loaded", True
        ):
            # Provider is google, no model set → gemini default
            assert get_llm_model() == "gemini-2.5-flash-lite"

            # Explicit model in user config overrides provider default
            with patch(
                "ontograph.config._user_config",
                {"llm": {"provider": "google", "model": "gemini-pro"}},
            ):
                assert get_llm_model() == "gemini-pro"


# ── reload_configs ──


class TestReloadConfigs:
    def test_reload_rereads_files(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".ontograph"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump({"llm": {"provider": "google"}}))

        with patch("ontograph.config.Path.home", return_value=tmp_path), patch(
            "ontograph.config.Path.cwd", return_value=tmp_path
        ):
            reload_configs()
            assert get_llm_provider() == "google"

            # Modify file and reload
            config_file.write_text(yaml.dump({"llm": {"provider": "openai"}}))
            reload_configs()
            assert get_llm_provider() == "openai"
