"""Artifact persistence — save and inspect run/fanout results."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

# Monotonic counter to disambiguate artifacts created in the same second.
_counter = 0

ARTIFACTS_DIR = Path.home() / ".bashful" / "artifacts"


def _ensure_dir() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _next_id(prefix: str) -> tuple[str, float]:
    global _counter
    _counter += 1
    ts = time.time()
    return f"{prefix}-{int(ts)}-{_counter}", ts


def save_run_artifact(
    result: object,
    prompt: str,
    cwd: str | None = None,
) -> str:
    """Save a RunResult as a JSON artifact. Returns the artifact ID."""
    _ensure_dir()
    artifact_id, ts = _next_id(f"run-{result.agent_id}")
    data = {
        "type": "run",
        "id": artifact_id,
        "timestamp": ts,
        "agent": result.agent_id,
        "mode": result.mode,
        "prompt": prompt,
        "command": result.command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "duration_s": result.duration_s,
        "cwd": cwd or os.getcwd(),
    }
    path = ARTIFACTS_DIR / f"{artifact_id}.json"
    path.write_text(json.dumps(data, indent=2))
    return artifact_id


def save_fanout_artifact(
    results: list[tuple[str, object]],
    prompt: str,
    mode: str = "read",
) -> str:
    """Save fanout results as a JSON artifact. Returns the artifact ID."""
    from bashful.fanout import FanoutError

    _ensure_dir()
    agent_ids = [aid for aid, _ in results]
    artifact_id, ts = _next_id(f"fanout-{'-'.join(agent_ids)}")

    per_agent = []
    for agent_id, result in results:
        if isinstance(result, FanoutError):
            per_agent.append({
                "agent": agent_id,
                "ok": False,
                "error": result.error,
                "exit_code": result.exit_code,
                "timed_out": result.timed_out,
            })
        else:
            per_agent.append({
                "agent": agent_id,
                "ok": result.ok,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "timed_out": result.timed_out,
                "duration_s": result.duration_s,
            })

    all_ok = all(r.ok for _, r in results)
    data = {
        "type": "fanout",
        "id": artifact_id,
        "timestamp": ts,
        "agents": agent_ids,
        "mode": mode,
        "prompt": prompt,
        "results": per_agent,
        "all_ok": all_ok,
    }
    path = ARTIFACTS_DIR / f"{artifact_id}.json"
    path.write_text(json.dumps(data, indent=2))
    return artifact_id


def _serialize_result(agent_id: str, result: object) -> dict:
    """Serialize a single agent result for artifact storage."""
    from bashful.fanout import FanoutError

    if isinstance(result, FanoutError):
        return {
            "agent": agent_id,
            "ok": False,
            "error": result.error,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
        }
    return {
        "agent": agent_id,
        "ok": result.ok,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "duration_s": result.duration_s,
    }


def save_review_artifact(data: dict, mode: str = "read") -> str:
    """Save review results as a JSON artifact. Returns the artifact ID."""
    _ensure_dir()
    agents = [aid for aid, _ in data["results"]]
    artifact_id, ts = _next_id(f"review-{'-'.join(agents)}")
    artifact = {
        "type": "review",
        "id": artifact_id,
        "timestamp": ts,
        "agents": agents,
        "mode": mode,
        "prompt": data["prompt"],
        "results": [_serialize_result(aid, r) for aid, r in data["results"]],
        "judge": data.get("judge"),
        "all_ok": all(r.ok for _, r in data["results"]),
    }
    path = ARTIFACTS_DIR / f"{artifact_id}.json"
    path.write_text(json.dumps(artifact, indent=2))
    return artifact_id


def save_dialectic_artifact(data: dict, mode: str = "read") -> str:
    """Save dialectic results as a JSON artifact. Returns the artifact ID."""
    _ensure_dir()
    t_id, t_result = data["thesis"]
    a_id, a_result = data["antithesis"]
    artifact_id, ts = _next_id(f"dialectic-{t_id}-{a_id}")
    artifact = {
        "type": "dialectic",
        "id": artifact_id,
        "timestamp": ts,
        "agents": [t_id, a_id],
        "mode": mode,
        "question": data["question"],
        "thesis": _serialize_result(t_id, t_result),
        "antithesis": _serialize_result(a_id, a_result),
        "synthesis": data.get("synthesis"),
        "all_ok": t_result.ok and a_result.ok,
    }
    path = ARTIFACTS_DIR / f"{artifact_id}.json"
    path.write_text(json.dumps(artifact, indent=2))
    return artifact_id


def save_matrix_artifact(
    rows: list[dict],
    agent_ids: list[str],
    mode: str = "read",
) -> str:
    """Save matrix results as a JSON artifact. Returns the artifact ID."""
    _ensure_dir()
    artifact_id, ts = _next_id(f"matrix-{'-'.join(agent_ids)}")
    prompts = []
    for row in rows:
        prompts.append({
            "prompt": row["prompt"],
            "results": [_serialize_result(aid, r) for aid, r in row["results"]],
        })
    all_ok = all(r.ok for row in rows for _, r in row["results"])
    artifact = {
        "type": "matrix",
        "id": artifact_id,
        "timestamp": ts,
        "agents": agent_ids,
        "mode": mode,
        "prompts": prompts,
        "all_ok": all_ok,
    }
    path = ARTIFACTS_DIR / f"{artifact_id}.json"
    path.write_text(json.dumps(artifact, indent=2))
    return artifact_id


def list_artifacts(limit: int = 20) -> list[dict]:
    """List recent artifacts, newest first."""
    if not ARTIFACTS_DIR.exists():
        return []
    files = sorted(
        ARTIFACTS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    artifacts = []
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text())
            artifacts.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return artifacts


def show_artifact(artifact_id: str) -> dict | None:
    """Load and return a single artifact by ID."""
    path = ARTIFACTS_DIR / f"{artifact_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
