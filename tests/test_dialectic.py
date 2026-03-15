"""Tests for the dialectic module."""

from unittest.mock import patch, MagicMock

from bashful.dialectic import (
    dialectic,
    _thesis_prompt,
    _antithesis_prompt,
    _synthesis_prompt,
)
from bashful.runner import RunResult
from bashful.fanout import FanoutError


class TestPromptBuilders:
    def test_thesis_prompt(self):
        result = _thesis_prompt("Use monorepos?")
        assert "in favor" in result
        assert "Use monorepos?" in result

    def test_antithesis_prompt(self):
        result = _antithesis_prompt("Use monorepos?")
        assert "against" in result
        assert "Use monorepos?" in result

    def test_synthesis_prompt(self):
        result = _synthesis_prompt(
            "Use monorepos?",
            "claude", "Monorepos are great.",
            "codex", "Monorepos are terrible.",
        )
        assert "Thesis" in result
        assert "Antithesis" in result
        assert "Synthesize" in result
        assert "claude" in result
        assert "codex" in result


class TestDialectic:
    def _mock_result(self, agent_id, text):
        return RunResult(
            agent_id=agent_id,
            command=[agent_id],
            stdout=text,
            stderr="",
            exit_code=0,
            duration_s=1.0,
            mode="read",
        )

    def test_dialectic_without_judge(self):
        def fake_get(agent_id):
            return MagicMock()

        def fake_run(agent, prompt, **kwargs):
            if "in favor" in prompt:
                return self._mock_result("claude", "Pro argument.")
            return self._mock_result("codex", "Con argument.")

        with (
            patch("bashful.dialectic.get_agent", side_effect=fake_get),
            patch("bashful.dialectic.run_agent", side_effect=fake_run),
        ):
            data = dialectic("claude", "codex", "Use monorepos?")

        assert data["question"] == "Use monorepos?"
        t_id, t_result = data["thesis"]
        assert t_id == "claude"
        assert "Pro" in t_result.stdout

        a_id, a_result = data["antithesis"]
        assert a_id == "codex"
        assert "Con" in a_result.stdout

        assert data["synthesis"] is None

    def test_dialectic_with_judge(self):
        call_count = 0

        def fake_get(agent_id):
            return MagicMock()

        def fake_run(agent, prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            if "in favor" in prompt:
                return self._mock_result("claude", "Pro.")
            if "against" in prompt:
                return self._mock_result("codex", "Con.")
            # Judge/synthesis call
            return self._mock_result("claude", "Balanced view.")

        with (
            patch("bashful.dialectic.get_agent", side_effect=fake_get),
            patch("bashful.dialectic.run_agent", side_effect=fake_run),
        ):
            data = dialectic("claude", "codex", "Monorepos?", judge="claude")

        assert data["synthesis"] is not None
        assert data["synthesis"]["ok"]
        assert "Balanced" in data["synthesis"]["stdout"]
        assert call_count == 3  # thesis + antithesis + synthesis

    def test_dialectic_unknown_agent(self):
        def fake_get(agent_id):
            if agent_id == "unknown":
                return None
            return MagicMock()

        def fake_run(agent, prompt, **kwargs):
            return self._mock_result("claude", "Pro.")

        with (
            patch("bashful.dialectic.get_agent", side_effect=fake_get),
            patch("bashful.dialectic.run_agent", side_effect=fake_run),
        ):
            data = dialectic("claude", "unknown", "Question?")

        a_id, a_result = data["antithesis"]
        assert isinstance(a_result, FanoutError)
        assert "Unknown" in a_result.error

    def test_dialectic_unknown_judge(self):
        def fake_get(agent_id):
            if agent_id == "nonexistent":
                return None
            return MagicMock()

        def fake_run(agent, prompt, **kwargs):
            return self._mock_result(agent.id if hasattr(agent, 'id') else "a", "text")

        with (
            patch("bashful.dialectic.get_agent", side_effect=fake_get),
            patch("bashful.dialectic.run_agent", side_effect=fake_run),
        ):
            data = dialectic("claude", "codex", "Q?", judge="nonexistent")

        assert data["synthesis"]["ok"] is False
        assert "Unknown" in data["synthesis"]["error"]
