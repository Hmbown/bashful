"""Matrix command — run multiple prompts across multiple agents."""

from __future__ import annotations

from bashful.agents import DEFAULT_MODE
from bashful.fanout import fanout


def matrix(
    agent_ids: list[str],
    prompts: list[str],
    *,
    timeout: float = 60.0,
    output_format: str | None = None,
    mode: str = DEFAULT_MODE,
    parallel: bool = False,
) -> list[dict]:
    """Run each prompt across all agents.

    Returns a list of dicts, one per prompt:
        [{"prompt": str, "results": [(agent_id, result), ...]}, ...]
    """
    rows = []
    for prompt in prompts:
        results = fanout(
            agent_ids,
            prompt,
            timeout=timeout,
            output_format=output_format,
            mode=mode,
            parallel=parallel,
        )
        rows.append({"prompt": prompt, "results": results})
    return rows
