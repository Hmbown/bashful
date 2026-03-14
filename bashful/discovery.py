"""Detect which agent CLIs are installed locally."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from bashful.agents import AgentInfo, load_agents


@dataclass(frozen=True)
class DiscoveryResult:
    id: str
    name: str
    installed: bool
    path: str | None


def _subcommand_available(executable_path: str, subcommand: str) -> bool:
    """Return True if *executable_path* exposes *subcommand*."""
    try:
        proc = subprocess.run(
            [executable_path, subcommand, "--help"],
            capture_output=True,
            timeout=5,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def check_agent(agent: AgentInfo) -> DiscoveryResult:
    """Check whether a single agent CLI is installed."""
    resolved = shutil.which(agent.executable)
    installed = resolved is not None
    if installed and agent.subcommand:
        installed = _subcommand_available(resolved, agent.subcommand)
    return DiscoveryResult(
        id=agent.id,
        name=agent.name,
        installed=installed,
        path=resolved if installed else None,
    )


def discover() -> list[DiscoveryResult]:
    """Discover install status for all cataloged agents."""
    return [check_agent(a) for a in load_agents()]
