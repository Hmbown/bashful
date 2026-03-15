"""Tests for the review module."""

from unittest.mock import patch, MagicMock

from bashful.review import review, _wrap_review_prompt, _build_judge_prompt
from bashful.runner import RunResult
from bashful.fanout import FanoutError


class TestWrapReviewPrompt:
    def test_wraps_with_review_instructions(self):
        result = _wrap_review_prompt("Check this plan.")
        assert "Review" in result
        assert "critique" in result
        assert "Check this plan." in result


class TestBuildJudgePrompt:
    def test_includes_reviewer_outputs(self):
        results = [
            ("claude", MagicMock(stdout="Looks risky.", ok=True)),
            ("codex", MagicMock(stdout="Seems fine.", ok=True)),
        ]
        prompt = _build_judge_prompt("Check this plan.", results)
        assert "claude" in prompt
        assert "codex" in prompt
        assert "Looks risky." in prompt
        assert "Seems fine." in prompt
        assert "Synthesize" in prompt

    def test_handles_error_results(self):
        results = [
            ("claude", FanoutError(agent_id="claude", error="not installed")),
        ]
        prompt = _build_judge_prompt("Check this.", results)
        assert "ERROR" in prompt
        assert "not installed" in prompt


class TestReview:
    def test_review_without_judge(self):
        mock_result = RunResult(
            agent_id="claude",
            command=["claude"],
            stdout="Good plan, minor risks.",
            stderr="",
            exit_code=0,
            duration_s=1.0,
            mode="read",
        )

        def fake_fanout(agent_ids, prompt, **kwargs):
            return [(aid, mock_result) for aid in agent_ids]

        with patch("bashful.review.fanout", side_effect=fake_fanout):
            data = review(["claude", "codex"], "Check this plan.")

        assert data["prompt"] == "Check this plan."
        assert len(data["results"]) == 2
        assert data["judge"] is None

    def test_review_with_judge(self):
        mock_result = RunResult(
            agent_id="claude",
            command=["claude"],
            stdout="Good plan.",
            stderr="",
            exit_code=0,
            duration_s=1.0,
            mode="read",
        )
        mock_judge = RunResult(
            agent_id="claude",
            command=["claude"],
            stdout="Consensus: plan is solid.",
            stderr="",
            exit_code=0,
            duration_s=2.0,
            mode="read",
        )

        def fake_fanout(agent_ids, prompt, **kwargs):
            return [(aid, mock_result) for aid in agent_ids]

        with (
            patch("bashful.review.fanout", side_effect=fake_fanout),
            patch("bashful.review.get_agent", return_value=MagicMock()),
            patch("bashful.review.run_agent", return_value=mock_judge),
        ):
            data = review(["claude", "codex"], "Check.", judge="claude")

        assert data["judge"] is not None
        assert data["judge"]["ok"]
        assert "solid" in data["judge"]["stdout"]

    def test_review_unknown_judge(self):
        mock_result = RunResult(
            agent_id="claude",
            command=["claude"],
            stdout="ok",
            stderr="",
            exit_code=0,
            duration_s=1.0,
            mode="read",
        )

        def fake_fanout(agent_ids, prompt, **kwargs):
            return [(aid, mock_result) for aid in agent_ids]

        with (
            patch("bashful.review.fanout", side_effect=fake_fanout),
            patch("bashful.review.get_agent", return_value=None),
        ):
            data = review(["claude"], "Check.", judge="nonexistent")

        assert data["judge"]["ok"] is False
        assert "Unknown" in data["judge"]["error"]
