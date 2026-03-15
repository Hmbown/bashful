"""Process supervision — launch, track, and manage background agent jobs."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from bashful.agents import AgentInfo

JOBS_DIR = Path.home() / ".bashful" / "jobs"

# In-session Popen handles (lost on process restart; PID-based fallback used then)
_handles: dict[str, subprocess.Popen] = {}


@dataclass
class Job:
    job_id: str
    agent_id: str
    prompt: str
    pid: int
    command: list[str]
    cwd: str
    started_at: float
    worktree: str | None = None

    @property
    def job_dir(self) -> Path:
        return JOBS_DIR / self.job_id

    @property
    def stdout_path(self) -> Path:
        return self.job_dir / "stdout.log"

    @property
    def stderr_path(self) -> Path:
        return self.job_dir / "stderr.log"

    @property
    def meta_path(self) -> Path:
        return self.job_dir / "meta.json"


@dataclass
class JobStatus:
    job_id: str
    agent_id: str
    pid: int
    state: str  # "running", "completed", "failed", "killed", "unknown", "lost"
    exit_code: int | None
    started_at: float
    ended_at: float | None
    duration_s: float | None
    log_dir: str
    worktree: str | None = None


def _gen_id() -> str:
    return secrets.token_hex(4)


def _write_status(job_dir: Path, state: str, exit_code: int | None) -> None:
    status_path = job_dir / "status.json"
    status_path.write_text(json.dumps({
        "state": state,
        "exit_code": exit_code,
        "ended_at": time.time(),
    }))


def _read_status(job_dir: Path) -> dict | None:
    status_path = job_dir / "status.json"
    if status_path.exists():
        return json.loads(status_path.read_text())
    return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def launch(
    agent: AgentInfo,
    prompt: str,
    *,
    cwd: str | None = None,
    worktree: str | None = None,
    output_format: str | None = None,
    mode: str = "read",
    jobs_dir: Path | None = None,
) -> Job:
    """Launch an agent in the background and return a Job handle.

    Args:
        agent: The agent to launch.
        prompt: The prompt to send.
        cwd: Working directory (overridden by worktree if set).
        worktree: Path to a worktree directory to use as cwd.
        output_format: Output format override.
        mode: Execution mode ("read" or "write").
        jobs_dir: Override jobs directory (for testing).
    """
    if agent.headless is None:
        raise ValueError(f"Agent {agent.id!r} has no headless invocation profile")

    resolved = shutil.which(agent.executable)
    if resolved is None:
        raise ValueError(f"Agent {agent.id!r} executable {agent.executable!r} not found in PATH")

    effective_cwd = worktree or cwd or os.getcwd()
    cmd = agent.headless.build_command(resolved, prompt, output_format, mode=mode)

    base = jobs_dir or JOBS_DIR
    job_id = _gen_id()
    job_dir = base / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    stdout_f = open(job_dir / "stdout.log", "w")
    stderr_f = open(job_dir / "stderr.log", "w")

    proc = subprocess.Popen(
        cmd,
        stdout=stdout_f,
        stderr=stderr_f,
        cwd=effective_cwd,
        start_new_session=True,  # detach from our process group
    )

    job = Job(
        job_id=job_id,
        agent_id=agent.id,
        prompt=prompt,
        pid=proc.pid,
        command=cmd,
        cwd=effective_cwd,
        started_at=time.time(),
        worktree=worktree,
    )

    # Save meta
    meta = asdict(job)
    (job_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Keep Popen handle for in-session polling
    _handles[job_id] = proc

    return job


def poll(job_id: str, *, jobs_dir: Path | None = None) -> JobStatus:
    """Check the status of a job."""
    base = jobs_dir or JOBS_DIR
    job_dir = base / job_id
    meta_path = job_dir / "meta.json"

    if not meta_path.exists():
        raise ValueError(f"Job {job_id!r} not found")

    meta = json.loads(meta_path.read_text())

    # Check for existing status file
    status = _read_status(job_dir)
    if status:
        ended = status["ended_at"]
        return JobStatus(
            job_id=job_id,
            agent_id=meta["agent_id"],
            pid=meta["pid"],
            state=status["state"],
            exit_code=status["exit_code"],
            started_at=meta["started_at"],
            ended_at=ended,
            duration_s=round(ended - meta["started_at"], 2) if ended else None,
            log_dir=str(job_dir),
            worktree=meta.get("worktree"),
        )

    # Check in-session handle first
    handle = _handles.get(job_id)
    if handle is not None:
        rc = handle.poll()
        if rc is not None:
            # Process finished
            state = "completed" if rc == 0 else "failed"
            _write_status(job_dir, state, rc)
            del _handles[job_id]
            ended = time.time()
            return JobStatus(
                job_id=job_id,
                agent_id=meta["agent_id"],
                pid=meta["pid"],
                state=state,
                exit_code=rc,
                started_at=meta["started_at"],
                ended_at=ended,
                duration_s=round(ended - meta["started_at"], 2),
                log_dir=str(job_dir),
                worktree=meta.get("worktree"),
            )
        # Still running
        return JobStatus(
            job_id=job_id,
            agent_id=meta["agent_id"],
            pid=meta["pid"],
            state="running",
            exit_code=None,
            started_at=meta["started_at"],
            ended_at=None,
            duration_s=None,
            log_dir=str(job_dir),
            worktree=meta.get("worktree"),
        )

    # Cross-session: no Popen handle — we cannot trust PID alone
    # (PIDs are recycled; the process may belong to someone else).
    pid = meta["pid"]
    if _pid_alive(pid):
        # PID exists but could be a different process; report "unknown".
        return JobStatus(
            job_id=job_id,
            agent_id=meta["agent_id"],
            pid=pid,
            state="unknown",
            exit_code=None,
            started_at=meta["started_at"],
            ended_at=None,
            duration_s=None,
            log_dir=str(job_dir),
            worktree=meta.get("worktree"),
        )

    # PID is dead and no status file — process ended between sessions
    _write_status(job_dir, "lost", None)
    return JobStatus(
        job_id=job_id,
        agent_id=meta["agent_id"],
        pid=pid,
        state="lost",
        exit_code=None,
        started_at=meta["started_at"],
        ended_at=None,
        duration_s=None,
        log_dir=str(job_dir),
        worktree=meta.get("worktree"),
    )


def list_jobs(
    *,
    state_filter: str | None = None,
    jobs_dir: Path | None = None,
) -> list[JobStatus]:
    """List all known jobs, optionally filtered by state."""
    base = jobs_dir or JOBS_DIR
    if not base.exists():
        return []

    results = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue
        try:
            status = poll(entry.name, jobs_dir=base)
            if state_filter is None or status.state == state_filter:
                results.append(status)
        except (ValueError, json.JSONDecodeError):
            continue
    return results


def kill_job(job_id: str, *, jobs_dir: Path | None = None) -> bool:
    """Kill a running job. Returns True if the signal was sent."""
    base = jobs_dir or JOBS_DIR
    job_dir = base / job_id
    meta_path = job_dir / "meta.json"

    if not meta_path.exists():
        raise ValueError(f"Job {job_id!r} not found")

    # Already finished?
    status = _read_status(job_dir)
    if status:
        return False

    meta = json.loads(meta_path.read_text())
    pid = meta["pid"]

    # Try in-session handle first
    handle = _handles.get(job_id)
    if handle is not None:
        handle.terminate()
        try:
            handle.wait(timeout=5)
        except subprocess.TimeoutExpired:
            handle.kill()
        _write_status(job_dir, "killed", handle.returncode)
        del _handles[job_id]
        return True

    # Cross-session: we only have the PID and cannot verify it still
    # belongs to the original job (PIDs are recycled).  Refuse to signal
    # rather than risk killing an unrelated process.
    return False


def read_logs(
    job_id: str,
    *,
    stream: str = "stdout",
    tail: int | None = None,
    jobs_dir: Path | None = None,
) -> str:
    """Read log output for a job."""
    base = jobs_dir or JOBS_DIR
    job_dir = base / job_id
    log_file = job_dir / f"{stream}.log"

    if not log_file.exists():
        raise ValueError(f"No {stream} log for job {job_id!r}")

    content = log_file.read_text()
    if tail is not None:
        lines = content.splitlines()
        content = "\n".join(lines[-tail:])
    return content
