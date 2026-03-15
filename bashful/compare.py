"""Compare mode — run multiple agents and optionally judge the results."""

from __future__ import annotations

from bashful.agents import DEFAULT_MODE, get_agent
from bashful.fanout import FanoutError, fanout
from bashful.normalize import normalize_fanout
from bashful.runner import run_agent


def compare(
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
    """Run *prompt* across *agent_ids* and optionally ask a judge to compare.

    Returns a dict with keys: prompt, results, summary, judge.
    """
    results = fanout(
        agent_ids,
        prompt,
        timeout=timeout,
        output_format=output_format,
        mode=mode,
        parallel=parallel,
    )

    summary = normalize_fanout(results)

    judge_result = None
    if judge:
        judge_result = _run_judge(judge, prompt, results, timeout=judge_timeout)

    return {
        "prompt": prompt,
        "results": results,
        "summary": summary,
        "judge": judge_result,
    }


def _build_judge_prompt(
    original_prompt: str,
    results: list[tuple[str, object]],
) -> str:
    """Build a transparent prompt for the judge agent."""
    parts = [
        f"Several agents were asked: {original_prompt!r}\n",
        "Their responses:\n",
    ]
    for agent_id, result in results:
        if isinstance(result, FanoutError):
            parts.append(f"--- {agent_id} ---\n[ERROR: {result.error}]\n")
        else:
            stdout = result.stdout.strip() if result.stdout else "(no output)"
            parts.append(f"--- {agent_id} ---\n{stdout}\n")

    parts.append(
        "\nCompare these responses. Which is best and why? Be concise."
    )
    return "\n".join(parts)


def _run_judge(
    judge_id: str,
    original_prompt: str,
    results: list[tuple[str, object]],
    *,
    timeout: float = 120.0,
) -> dict:
    """Run a judge agent to synthesize the comparison."""
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
