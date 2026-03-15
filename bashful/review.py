"""Review command — structured critique via multi-agent comparison."""

from __future__ import annotations

from bashful.agents import DEFAULT_MODE, get_agent
from bashful.fanout import FanoutError, fanout
from bashful.runner import run_agent


def _wrap_review_prompt(prompt: str) -> str:
    """Wrap a user prompt with review-oriented instructions."""
    return (
        f"Review the following and provide a concise critique. "
        f"Focus on risks, gaps, and actionable improvements.\n\n"
        f"{prompt}"
    )


def _build_judge_prompt(original_prompt: str, results: list[tuple[str, object]]) -> str:
    """Build a synthesis prompt for the judge from reviewer outputs."""
    parts = [
        f"Multiple reviewers were asked to critique: {original_prompt!r}\n",
        "Their reviews:\n",
    ]
    for agent_id, result in results:
        if isinstance(result, FanoutError):
            parts.append(f"--- {agent_id} ---\n[ERROR: {result.error}]\n")
        else:
            stdout = result.stdout.strip() if result.stdout else "(no output)"
            parts.append(f"--- {agent_id} ---\n{stdout}\n")

    parts.append(
        "\nSynthesize these reviews into a single coherent assessment. "
        "Highlight consensus, resolve contradictions, and prioritize "
        "the most important findings. Be concise."
    )
    return "\n".join(parts)


def review(
    agent_ids: list[str],
    prompt: str,
    *,
    timeout: float = 60.0,
    output_format: str | None = None,
    mode: str = DEFAULT_MODE,
    parallel: bool = False,
    judge: str | None = None,
    judge_timeout: float = 120.0,
) -> dict:
    """Run a review workflow: fan out a review prompt, optionally synthesize.

    Returns a dict with keys: prompt, results, judge.
    """
    review_prompt = _wrap_review_prompt(prompt)

    results = fanout(
        agent_ids,
        review_prompt,
        timeout=timeout,
        output_format=output_format,
        mode=mode,
        parallel=parallel,
    )

    judge_result = None
    if judge:
        judge_result = _run_judge(judge, prompt, results, timeout=judge_timeout)

    return {
        "prompt": prompt,
        "results": results,
        "judge": judge_result,
    }


def _run_judge(
    judge_id: str,
    original_prompt: str,
    results: list[tuple[str, object]],
    *,
    timeout: float = 120.0,
) -> dict:
    """Run a judge agent to synthesize reviews."""
    agent = get_agent(judge_id)
    if agent is None:
        return {
            "agent": judge_id,
            "ok": False,
            "error": f"Unknown judge agent: {judge_id!r}",
        }

    judge_prompt = _build_judge_prompt(original_prompt, results)

    try:
        result = run_agent(agent, judge_prompt, timeout=timeout)
        return {
            "agent": judge_id,
            "ok": result.ok,
            "stdout": result.stdout.strip(),
            "exit_code": result.exit_code,
            "duration_s": result.duration_s,
        }
    except ValueError as e:
        return {"agent": judge_id, "ok": False, "error": str(e)}
