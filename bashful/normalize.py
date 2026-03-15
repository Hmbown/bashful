"""Lightweight normalization helpers for run/fanout results."""

from __future__ import annotations


def normalize_run(result: object, *, preview_len: int = 200) -> dict:
    """Normalize a RunResult into a consistent summary dict.

    Returns:
        {agent, ok, timed_out, exit_code, stdout_preview, stderr_preview,
         mode, duration_s}
    """
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    return {
        "agent": result.agent_id,
        "ok": result.ok,
        "timed_out": result.timed_out,
        "exit_code": result.exit_code,
        "stdout_preview": stdout.strip()[:preview_len],
        "stderr_preview": stderr.strip()[:preview_len],
        "mode": getattr(result, "mode", ""),
        "duration_s": result.duration_s,
    }


def normalize_fanout(
    results: list[tuple[str, object]],
    *,
    preview_len: int = 200,
) -> dict:
    """Normalize fanout results into a summary dict.

    Returns:
        {all_ok, count, results: [normalized items]}
    """
    from bashful.fanout import FanoutError

    items = []
    for agent_id, result in results:
        if isinstance(result, FanoutError):
            items.append({
                "agent": agent_id,
                "ok": False,
                "timed_out": result.timed_out,
                "exit_code": result.exit_code,
                "stdout_preview": "",
                "stderr_preview": "",
                "mode": "",
                "duration_s": None,
                "error": result.error,
            })
        else:
            items.append(normalize_run(result, preview_len=preview_len))

    all_ok = all(item["ok"] for item in items) if items else True
    return {
        "all_ok": all_ok,
        "count": len(items),
        "results": items,
    }
