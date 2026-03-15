"""Tests for the matrix module."""

from unittest.mock import patch

from bashful.matrix import matrix
from bashful.runner import RunResult
from bashful.fanout import FanoutError


def _mock_result(agent_id, text="ok"):
    return RunResult(
        agent_id=agent_id,
        command=[agent_id],
        stdout=text,
        stderr="",
        exit_code=0,
        duration_s=1.0,
        mode="read",
    )


class TestMatrix:
    def test_single_prompt(self):
        def fake_fanout(agent_ids, prompt, **kwargs):
            return [(aid, _mock_result(aid, "READY")) for aid in agent_ids]

        with patch("bashful.matrix.fanout", side_effect=fake_fanout):
            rows = matrix(["claude"], ["Reply READY"])

        assert len(rows) == 1
        assert rows[0]["prompt"] == "Reply READY"
        assert len(rows[0]["results"]) == 1
        assert rows[0]["results"][0][0] == "claude"

    def test_multiple_prompts_and_agents(self):
        def fake_fanout(agent_ids, prompt, **kwargs):
            return [(aid, _mock_result(aid, prompt)) for aid in agent_ids]

        with patch("bashful.matrix.fanout", side_effect=fake_fanout):
            rows = matrix(["claude", "codex"], ["p1", "p2"])

        assert len(rows) == 2
        assert rows[0]["prompt"] == "p1"
        assert rows[1]["prompt"] == "p2"
        assert len(rows[0]["results"]) == 2
        assert len(rows[1]["results"]) == 2

    def test_passes_kwargs(self):
        captured = {}

        def fake_fanout(agent_ids, prompt, **kwargs):
            captured.update(kwargs)
            return [(aid, _mock_result(aid)) for aid in agent_ids]

        with patch("bashful.matrix.fanout", side_effect=fake_fanout):
            matrix(["claude"], ["p1"], timeout=30.0, parallel=True, mode="write")

        assert captured["timeout"] == 30.0
        assert captured["parallel"] is True
        assert captured["mode"] == "write"

    def test_handles_errors(self):
        def fake_fanout(agent_ids, prompt, **kwargs):
            return [("bad", FanoutError(agent_id="bad", error="Unknown"))]

        with patch("bashful.matrix.fanout", side_effect=fake_fanout):
            rows = matrix(["bad"], ["p1"])

        assert len(rows) == 1
        _, result = rows[0]["results"][0]
        assert isinstance(result, FanoutError)

    def test_preserves_prompt_order(self):
        calls = []

        def fake_fanout(agent_ids, prompt, **kwargs):
            calls.append(prompt)
            return [(aid, _mock_result(aid, prompt)) for aid in agent_ids]

        with patch("bashful.matrix.fanout", side_effect=fake_fanout):
            rows = matrix(["claude"], ["first", "second", "third"])

        assert calls == ["first", "second", "third"]
        assert [r["prompt"] for r in rows] == ["first", "second", "third"]
