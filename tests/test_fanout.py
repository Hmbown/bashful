"""Tests for multi-agent fanout."""

from unittest.mock import patch, MagicMock

from bashful.fanout import fanout, FanoutError
from bashful.runner import RunResult


def _mock_run_agent(agent, prompt, *, timeout=60.0, output_format=None, mode="read"):
    """Stub that returns a successful RunResult."""
    return RunResult(
        agent_id=agent.id,
        command=[agent.executable, "-p", prompt],
        stdout=f"Response from {agent.id}",
        stderr="",
        exit_code=0,
        duration_s=0.1,
        mode=mode,
    )


class TestFanout:
    def test_successful_fanout(self):
        with (
            patch("bashful.fanout.run_agent", side_effect=_mock_run_agent),
            patch("bashful.runner.shutil.which", return_value="/usr/bin/fake"),
        ):
            results = fanout(["claude", "codex"], "hello")

        assert len(results) == 2
        assert results[0][0] == "claude"
        assert results[1][0] == "codex"
        assert results[0][1].ok
        assert results[1][1].ok
        assert "claude" in results[0][1].stdout
        assert "codex" in results[1][1].stdout

    def test_unknown_agent_returns_error(self):
        results = fanout(["nonexistent"], "hello")
        assert len(results) == 1
        agent_id, result = results[0]
        assert agent_id == "nonexistent"
        assert isinstance(result, FanoutError)
        assert not result.ok
        assert "Unknown agent" in result.error

    def test_mixed_known_and_unknown(self):
        with (
            patch("bashful.fanout.run_agent", side_effect=_mock_run_agent),
            patch("bashful.runner.shutil.which", return_value="/usr/bin/fake"),
        ):
            results = fanout(["claude", "nonexistent", "codex"], "hello")

        assert len(results) == 3
        assert results[0][1].ok
        assert isinstance(results[1][1], FanoutError)
        assert results[2][1].ok

    def test_fanout_passes_mode(self):
        calls = []

        def capture_run(agent, prompt, *, timeout=60.0, output_format=None, mode="read"):
            calls.append(mode)
            return _mock_run_agent(agent, prompt, mode=mode)

        with (
            patch("bashful.fanout.run_agent", side_effect=capture_run),
            patch("bashful.runner.shutil.which", return_value="/usr/bin/fake"),
        ):
            fanout(["claude"], "hello", mode="write")

        assert calls == ["write"]

    def test_fanout_handles_runner_error(self):
        def fail_run(agent, prompt, **kwargs):
            raise ValueError("not found in PATH")

        with patch("bashful.fanout.run_agent", side_effect=fail_run):
            results = fanout(["claude"], "hello")

        assert len(results) == 1
        assert isinstance(results[0][1], FanoutError)
        assert "not found" in results[0][1].error

    def test_timed_out_result_not_ok(self):
        """A timed-out RunResult should not be considered ok."""
        def timeout_run(agent, prompt, **kwargs):
            return RunResult(
                agent_id=agent.id,
                command=[agent.executable],
                stdout="",
                stderr="",
                exit_code=-1,
                duration_s=60.0,
                timed_out=True,
                mode="read",
            )

        with patch("bashful.fanout.run_agent", side_effect=timeout_run):
            results = fanout(["claude"], "hello")

        assert len(results) == 1
        assert not results[0][1].ok
        assert results[0][1].timed_out

    def test_empty_agent_list(self):
        results = fanout([], "hello")
        assert results == []
