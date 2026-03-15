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
        assert "bashful fanout" in doc

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

    def test_contains_execution_modes(self):
        doc = generate_skill_doc()
        assert "Execution Modes" in doc
        assert "`read`" in doc
        assert "`write`" in doc
        assert "-m write" in doc
        # Should not overclaim enforcement
        assert "signal" in doc.lower() or "intent" in doc.lower()

    def test_contains_fanout_section(self):
        doc = generate_skill_doc()
        assert "fanout" in doc.lower()
        assert "Multi-agent fanout" in doc

    def test_contains_parallel_fanout(self):
        doc = generate_skill_doc()
        assert "--parallel" in doc

    def test_contains_artifact_commands(self):
        doc = generate_skill_doc()
        assert "--save" in doc
        assert "bashful artifacts" in doc

    def test_contains_artifact_workflow(self):
        doc = generate_skill_doc()
        assert "Save and inspect artifacts" in doc or "artifact" in doc.lower()

    def test_contains_bashful_vs_acz(self):
        doc = generate_skill_doc()
        assert "ACZ" in doc

    def test_agents_table_includes_modes(self):
        doc = generate_skill_doc()
        # The agents table should have a Modes column
        assert "| Modes |" in doc
        assert "read, write" in doc

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

    def test_agents_include_modes(self):
        meta = get_skill_metadata()
        # agents is now a list of dicts with id and modes
        claude_entry = next(a for a in meta["agents"] if a["id"] == "claude")
        assert "read" in claude_entry["modes"]
        assert "write" in claude_entry["modes"]

    def test_metadata_includes_mode_info(self):
        meta = get_skill_metadata()
        assert meta["modes"] == ["read", "write"]
        assert meta["default_mode"] == "read"

    def test_commands_include_new_features(self):
        meta = get_skill_metadata()
        assert "launch" in meta["commands"]
        assert "jobs" in meta["commands"]
        assert "worktree create" in meta["commands"]
        assert "skill" in meta["commands"]
        assert "fanout" in meta["commands"]
        assert "artifacts" in meta["commands"]
        assert "artifacts show" in meta["commands"]
