"""Sequential multi-agent fanout — run the same prompt across several agents."""

from __future__ import annotations

from dataclasses import dataclass

from bashful.agents import DEFAULT_MODE, get_agent
from bashful.runner import RunResult, run_agent


@dataclass(frozen=True)
class FanoutError:
    """Placeholder result when an agent cannot be invoked."""
    agent_id: str
    error: str
    ok: bool = False
    timed_out: bool = False
    exit_code: int = -1


def fanout(
    agent_ids: list[str],
    prompt: str,
    *,
    timeout: float = 60.0,
    output_format: str | None = None,
    mode: str = DEFAULT_MODE,
) -> list[tuple[str, RunResult | FanoutError]]:
    """Run *prompt* against each agent in *agent_ids* sequentially.

    Returns a list of ``(agent_id, result)`` tuples in the same order as
    *agent_ids*.  If an agent is unknown or cannot be run, the result is a
    :class:`FanoutError` instead of a :class:`RunResult`.
    """
    results: list[tuple[str, RunResult | FanoutError]] = []

    for agent_id in agent_ids:
        agent = get_agent(agent_id)
        if agent is None:
            results.append((agent_id, FanoutError(
                agent_id=agent_id,
                error=f"Unknown agent: {agent_id!r}",
            )))
            continue

        try:
            result = run_agent(
                agent,
                prompt,
                timeout=timeout,
                output_format=output_format,
                mode=mode,
            )
            results.append((agent_id, result))
        except ValueError as exc:
            results.append((agent_id, FanoutError(
                agent_id=agent_id,
                error=str(exc),
            )))

    return results
