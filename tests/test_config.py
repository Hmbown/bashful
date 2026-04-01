"""Tests for configuration override support."""

import json

from bashful.config import (
    apply_overrides,
    get_agent_overrides,
    load_config,
    show_config,
)


class TestLoadConfig:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bashful.config.CONFIG_FILE", tmp_path / "nope.json")
        assert load_config() == {}

    def test_valid_config(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"agents": {"gemini": {"modes": ["read", "write"]}}}))
        monkeypatch.setattr("bashful.config.CONFIG_FILE", cfg)
        result = load_config()
        assert result["agents"]["gemini"]["modes"] == ["read", "write"]

    def test_invalid_json_returns_empty(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.json"
        cfg.write_text("not json")
        monkeypatch.setattr("bashful.config.CONFIG_FILE", cfg)
        assert load_config() == {}

    def test_non_dict_returns_empty(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps([1, 2, 3]))
        monkeypatch.setattr("bashful.config.CONFIG_FILE", cfg)
        assert load_config() == {}


class TestGetAgentOverrides:
    def test_extracts_agents_section(self):
        config = {"agents": {"gemini": {"modes": ["read", "write"]}}}
        result = get_agent_overrides(config)
        assert result == {"gemini": {"modes": ["read", "write"]}}

    def test_empty_config(self):
        assert get_agent_overrides({}) == {}

    def test_no_agents_key(self):
        assert get_agent_overrides({"other": "stuff"}) == {}


class TestApplyOverrides:
    def test_overrides_modes(self):
        data = [{"id": "gemini", "modes": ["read"]}, {"id": "claude", "modes": ["read", "write"]}]
        overrides = {"gemini": {"modes": ["read", "write"]}}
        result = apply_overrides(data, overrides)
        assert result[0]["modes"] == ["read", "write"]
        assert result[1]["modes"] == ["read", "write"]  # unchanged

    def test_ignores_unknown_fields(self):
        data = [{"id": "gemini", "modes": ["read"]}]
        overrides = {"gemini": {"modes": ["read", "write"], "bogus": "ignored"}}
        result = apply_overrides(data, overrides)
        assert result[0]["modes"] == ["read", "write"]
        assert "bogus" not in result[0]

    def test_empty_overrides_noop(self):
        data = [{"id": "gemini", "modes": ["read"]}]
        result = apply_overrides(data, {})
        assert result[0]["modes"] == ["read"]

    def test_unknown_agent_ignored(self):
        data = [{"id": "gemini", "modes": ["read"]}]
        overrides = {"nonexistent": {"modes": ["read", "write"]}}
        result = apply_overrides(data, overrides)
        assert result[0]["modes"] == ["read"]


class TestShowConfig:
    def test_no_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bashful.config.CONFIG_FILE", tmp_path / "nope.json")
        output = show_config()
        assert "no config file" in output

    def test_with_overrides(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"agents": {"gemini": {"modes": ["read", "write"]}}}))
        monkeypatch.setattr("bashful.config.CONFIG_FILE", cfg)
        output = show_config()
        assert "gemini" in output
        assert "Agent overrides" in output


class TestAgentLoadWithOverrides:
    def test_overrides_applied_to_catalog(self, tmp_path, monkeypatch):
        """Verify load_agents() merges user config overrides."""
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"agents": {"gemini": {"modes": ["read", "write"]}}}))
        monkeypatch.setattr("bashful.config.CONFIG_FILE", cfg)

        from bashful.agents import load_agents
        agents = load_agents()
        gemini = next(a for a in agents if a.id == "gemini")
        assert "write" in gemini.modes

    def test_no_config_uses_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr("bashful.config.CONFIG_FILE", tmp_path / "nope.json")

        from bashful.agents import load_agents
        agents = load_agents()
        gemini = next(a for a in agents if a.id == "gemini")
        assert gemini.modes == ["read", "write"]  # default from catalog
