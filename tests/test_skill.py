"""Tests for skill document generation."""

from unittest.mock import patch, MagicMock

from bashful.skill import generate_skill_doc, get_skill_metadata


class TestGenerateSkillDoc:
    def test_contains_commands(self):
        doc = generate_skill_doc()
        assert "bashful list" in doc
        assert "bashful run" in doc
        assert "bashful launch" in doc
        assert "bashful worktree" in doc
        assert "bashful skill" in doc

    def test_contains_agents(self):
        doc = generate_skill_doc()
        assert "claude" in doc.lower()
        assert "codex" in doc.lower()
        assert "gemini" in doc.lower()
        assert "qwen" in doc.lower()
        assert "opencode" in doc.lower()

    def test_contains_workflows(self):
        doc = generate_skill_doc()
        assert "Discover" in doc
        assert "one-shot" in doc.lower() or "Run a" in doc
        assert "background" in doc.lower()
        assert "worktree" in doc.lower()

    def test_live_state_disabled_by_default(self):
        doc = generate_skill_doc()
        assert "Current State" not in doc

    def test_live_state_enabled(self):
        mock_result = MagicMock()
        mock_result.installed = True
        mock_result.id = "claude"
        mock_result.path = "/usr/bin/claude"

        with patch("bashful.discovery.discover", return_value=[mock_result]):
            doc = generate_skill_doc(include_state=True)

        assert "Current State" in doc
        assert "1/1" in doc


class TestGetSkillMetadata:
    def test_structure(self):
        meta = get_skill_metadata()
        assert meta["name"] == "bashful"
        assert "version" in meta
        assert isinstance(meta["agents"], list)
        assert isinstance(meta["commands"], list)
        assert "claude" in meta["agents"]

    def test_commands_include_new_features(self):
        meta = get_skill_metadata()
        assert "launch" in meta["commands"]
        assert "jobs" in meta["commands"]
        assert "worktree create" in meta["commands"]
        assert "skill" in meta["commands"]
