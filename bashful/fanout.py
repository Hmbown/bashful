"""Multi-agent fanout — run the same prompt across several agents."""

from __future__ import annotations

import concurrent.futures
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


def _run_one(
    agent_id: str,
    prompt: str,
    *,
    timeout: float,
    output_format: str | None,
    mode: str,
) -> tuple[str, RunResult | FanoutError]:
    agent = get_agent(agent_id)
    if agent is None:
        return (agent_id, FanoutError(
            agent_id=agent_id,
            error=f"Unknown agent: {agent_id!r}",
        ))
    try:
        result = run_agent(
            agent,
            prompt,
            timeout=timeout,
            output_format=output_format,
            mode=mode,
        )
        return (agent_id, result)
    except Exception as exc:
        return (agent_id, FanoutError(
            agent_id=agent_id,
            error=str(exc),
        ))


def fanout(
    agent_ids: list[str],
    prompt: str,
    *,
    timeout: float = 60.0,
    output_format: str | None = None,
    mode: str = DEFAULT_MODE,
    parallel: bool = False,
) -> list[tuple[str, RunResult | FanoutError]]:
    """Run *prompt* against each agent in *agent_ids*.

    Returns a list of ``(agent_id, result)`` tuples in the same order as
    *agent_ids*.  If an agent is unknown or cannot be run, the result is a
    :class:`FanoutError` instead of a :class:`RunResult`.

    When *parallel* is True, agents run concurrently using a thread pool.
    Sequential execution remains the default for predictability.
    """
    if parallel and len(agent_ids) > 1:
        return _fanout_parallel(
            agent_ids, prompt,
            timeout=timeout, output_format=output_format, mode=mode,
        )
    return _fanout_sequential(
        agent_ids, prompt,
        timeout=timeout, output_format=output_format, mode=mode,
    )


def _fanout_sequential(
    agent_ids: list[str],
    prompt: str,
    *,
    timeout: float,
    output_format: str | None,
    mode: str,
) -> list[tuple[str, RunResult | FanoutError]]:
    results: list[tuple[str, RunResult | FanoutError]] = []
    for agent_id in agent_ids:
        results.append(_run_one(
            agent_id, prompt,
            timeout=timeout, output_format=output_format, mode=mode,
        ))
    return results


MAX_PARALLEL_WORKERS = 4


def _fanout_parallel(
    agent_ids: list[str],
    prompt: str,
    *,
    timeout: float,
    output_format: str | None,
    mode: str,
) -> list[tuple[str, RunResult | FanoutError]]:
    max_workers = min(len(agent_ids), MAX_PARALLEL_WORKERS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        # Use index-based tracking so duplicate agent ids don't collide
        futures: dict[concurrent.futures.Future, int] = {}
        for idx, agent_id in enumerate(agent_ids):
            fut = pool.submit(
                _run_one, agent_id, prompt,
                timeout=timeout, output_format=output_format, mode=mode,
            )
            futures[fut] = idx
        # Collect results preserving original order
        results: list[tuple[str, RunResult | FanoutError] | None] = [None] * len(agent_ids)
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                aid = agent_ids[idx]
                results[idx] = (aid, FanoutError(agent_id=aid, error=str(exc)))
    return results  # type: ignore[return-value]
