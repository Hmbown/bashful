"""Dialectic command — thesis / antithesis / synthesis workflow."""

from __future__ import annotations

from bashful.agents import DEFAULT_MODE, get_agent
from bashful.fanout import FanoutError
from bashful.runner import RunResult, run_agent


def _thesis_prompt(question: str) -> str:
    return (
        f"Take a clear position in favor of the following and argue for it. "
        f"Be concise and direct.\n\n{question}"
    )


def _antithesis_prompt(question: str) -> str:
    return (
        f"Take a clear position against the following and argue against it. "
        f"Be concise and direct.\n\n{question}"
    )


def _synthesis_prompt(
    question: str,
    thesis_agent: str,
    thesis_text: str,
    antithesis_agent: str,
    antithesis_text: str,
) -> str:
    return (
        f"A question was posed: {question!r}\n\n"
        f"--- Thesis ({thesis_agent}) ---\n{thesis_text}\n\n"
        f"--- Antithesis ({antithesis_agent}) ---\n{antithesis_text}\n\n"
        f"Synthesize these opposing views. Identify what each side gets right, "
        f"where they conflict, and propose a balanced resolution. Be concise."
    )


def _run_one(
    agent_id: str,
    prompt: str,
    *,
    timeout: float,
    output_format: str | None,
    mode: str,
) -> tuple[str, RunResult | FanoutError]:
    """Run a single agent, returning (agent_id, result)."""
    agent = get_agent(agent_id)
    if agent is None:
        return (agent_id, FanoutError(
            agent_id=agent_id,
            error=f"Unknown agent: {agent_id!r}",
        ))
    try:
        result = run_agent(
            agent, prompt,
            timeout=timeout, output_format=output_format, mode=mode,
        )
        return (agent_id, result)
    except Exception as exc:
        return (agent_id, FanoutError(agent_id=agent_id, error=str(exc)))


def dialectic(
    agent_a: str,
    agent_b: str,
    question: str,
    *,
    timeout: float = 60.0,
    output_format: str | None = None,
    mode: str = DEFAULT_MODE,
    judge: str | None = None,
    judge_timeout: float = 120.0,
) -> dict:
    """Run a thesis/antithesis/synthesis dialectic.

    *agent_a* argues the thesis, *agent_b* argues the antithesis.
    If *judge* is provided, a third agent synthesizes.

    Returns a dict with keys: question, thesis, antithesis, synthesis.
    """
    thesis_id, thesis_result = _run_one(
        agent_a, _thesis_prompt(question),
        timeout=timeout, output_format=output_format, mode=mode,
    )
    antithesis_id, antithesis_result = _run_one(
        agent_b, _antithesis_prompt(question),
        timeout=timeout, output_format=output_format, mode=mode,
    )

    synthesis = None
    if judge:
        thesis_text = _get_output(thesis_result)
        antithesis_text = _get_output(antithesis_result)
        synthesis = _run_synthesis(
            judge, question,
            thesis_id, thesis_text,
            antithesis_id, antithesis_text,
            timeout=judge_timeout,
        )

    return {
        "question": question,
        "thesis": (thesis_id, thesis_result),
        "antithesis": (antithesis_id, antithesis_result),
        "synthesis": synthesis,
    }


def _get_output(result: RunResult | FanoutError) -> str:
    """Extract display text from a result."""
    if isinstance(result, FanoutError):
        return f"[ERROR: {result.error}]"
    return result.stdout.strip() if result.stdout else "(no output)"


def _run_synthesis(
    judge_id: str,
    question: str,
    thesis_agent: str,
    thesis_text: str,
    antithesis_agent: str,
    antithesis_text: str,
    *,
    timeout: float = 120.0,
) -> dict:
    """Run the synthesis step via a judge agent."""
    agent = get_agent(judge_id)
    if agent is None:
        return {
            "agent": judge_id,
            "ok": False,
            "error": f"Unknown judge agent: {judge_id!r}",
        }

    prompt = _synthesis_prompt(
        question, thesis_agent, thesis_text, antithesis_agent, antithesis_text,
    )

    try:
        result = run_agent(agent, prompt, timeout=timeout)
        return {
            "agent": judge_id,
            "ok": result.ok,
            "stdout": result.stdout.strip(),
            "exit_code": result.exit_code,
            "duration_s": result.duration_s,
        }
    except ValueError as e:
        return {"agent": judge_id, "ok": False, "error": str(e)}
