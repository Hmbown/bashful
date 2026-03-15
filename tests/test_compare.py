"""Tests for compare/judge mode."""

from unittest.mock import patch

from bashful.compare import _build_judge_prompt, compare
from bashful.fanout import FanoutError
from bashful.runner import RunResult


def _mock_run_agent(agent, prompt, *, timeout=60.0, output_format=None, mode="read"):
    return RunResult(
        agent_id=agent.id,
        command=[agent.executable, "-p", prompt],
        stdout=f"Response from {agent.id}",
        stderr="",
        exit_code=0,
        duration_s=0.5,
        mode=mode,
    )


class TestCompare:
    def test_basic_compare(self):
        with (
            patch("bashful.fanout.run_agent", side_effect=_mock_run_agent),
            patch("bashful.runner.shutil.which", return_value="/usr/bin/fake"),
        ):
            data = compare(["claude", "codex"], "hello")

        assert data["prompt"] == "hello"
        assert len(data["results"]) == 2
        assert data["summary"]["all_ok"] is True
        assert data["judge"] is None

    def test_compare_with_judge(self):
        def judge_run(agent, prompt, *, timeout=60.0, output_format=None, mode="read"):
            return RunResult(
                agent_id=agent.id,
                command=[agent.executable],
                stdout="Claude is better because...",
                stderr="",
                exit_code=0,
                duration_s=1.0,
                mode=mode,
            )

        with (
            patch("bashful.fanout.run_agent", side_effect=_mock_run_agent),
            patch("bashful.compare.run_agent", side_effect=judge_run),
            patch("bashful.runner.shutil.which", return_value="/usr/bin/fake"),
        ):
            data = compare(["claude", "codex"], "hello", judge="gemini")

        assert data["judge"] is not None
        assert data["judge"]["agent"] == "gemini"
        assert data["judge"]["ok"] is True
        assert "better" in data["judge"]["stdout"]

    def test_compare_unknown_judge(self):
        with (
            patch("bashful.fanout.run_agent", side_effect=_mock_run_agent),
            patch("bashful.runner.shutil.which", return_value="/usr/bin/fake"),
        ):
            data = compare(["claude"], "hello", judge="nonexistent")

        assert data["judge"]["ok"] is False
        assert "Unknown" in data["judge"]["error"]

    def test_compare_includes_summary(self):
        with (
            patch("bashful.fanout.run_agent", side_effect=_mock_run_agent),
            patch("bashful.runner.shutil.which", return_value="/usr/bin/fake"),
        ):
            data = compare(["claude"], "hello")

        assert "all_ok" in data["summary"]
        assert "count" in data["summary"]
        assert data["summary"]["count"] == 1


class TestBuildJudgePrompt:
    def test_includes_original_prompt(self):
        results = [("claude", RunResult(
            agent_id="claude", command=[], stdout="hi", stderr="",
            exit_code=0, duration_s=0.1,
        ))]
        prompt = _build_judge_prompt("test prompt", results)
        assert "test prompt" in prompt

    def test_includes_agent_output(self):
        results = [
            ("claude", RunResult(
                agent_id="claude", command=[], stdout="answer A", stderr="",
                exit_code=0, duration_s=0.1,
            )),
            ("codex", RunResult(
                agent_id="codex", command=[], stdout="answer B", stderr="",
                exit_code=0, duration_s=0.2,
            )),
        ]
        prompt = _build_judge_prompt("q", results)
        assert "--- claude ---" in prompt
        assert "answer A" in prompt
        assert "--- codex ---" in prompt
        assert "answer B" in prompt

    def test_handles_error_result(self):
        results = [
            ("bad", FanoutError(agent_id="bad", error="not found")),
        ]
        prompt = _build_judge_prompt("q", results)
        assert "--- bad ---" in prompt
        assert "ERROR" in prompt

    def test_ends_with_comparison_instruction(self):
        results = [("a", RunResult(
            agent_id="a", command=[], stdout="x", stderr="",
            exit_code=0, duration_s=0.1,
        ))]
        prompt = _build_judge_prompt("q", results)
        assert "Compare" in prompt
