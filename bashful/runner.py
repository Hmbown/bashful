"""Run agent CLIs as subprocesses."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass

from bashful.agents import AgentInfo


@dataclass(frozen=True)
class RunResult:
    agent_id: str
    command: list[str]
    stdout: str
    stderr: str
    exit_code: int
    duration_s: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def run_agent(
    agent: AgentInfo,
    prompt: str,
    *,
    timeout: float = 60.0,
    cwd: str | None = None,
    output_format: str | None = None,
) -> RunResult:
    """Run an agent CLI in headless mode and return the result.

    Args:
        agent: The agent to run.
        prompt: The prompt to send.
        timeout: Max seconds to wait (default 60).
        cwd: Working directory for the subprocess.
        output_format: Output format override (e.g. "text", "json").

    Returns:
        RunResult with stdout, stderr, exit code, and timing.

    Raises:
        ValueError: If the agent has no headless profile or is not installed.
    """
    if agent.headless is None:
        raise ValueError(f"Agent {agent.id!r} has no headless invocation profile")

    resolved = shutil.which(agent.executable)
    if resolved is None:
        raise ValueError(f"Agent {agent.id!r} executable {agent.executable!r} not found in PATH")

    cmd = agent.headless.build_command(resolved, prompt, output_format)

    t0 = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        exit_code = -1
        timed_out = True
    duration = time.monotonic() - t0

    return RunResult(
        agent_id=agent.id,
        command=cmd,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_s=round(duration, 2),
        timed_out=timed_out,
    )


def get_version(agent: AgentInfo, *, timeout: float = 10.0) -> str | None:
    """Get the version string of an installed agent CLI.

    Returns the first line of stdout, or None if the command fails.
    """
    resolved = shutil.which(agent.executable)
    if resolved is None:
        return None
    if not agent.version_args:
        return None

    cmd = [resolved] + list(agent.version_args)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None
