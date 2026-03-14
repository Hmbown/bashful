"""Health checks for agent CLIs — version + live ping."""

from __future__ import annotations

from dataclasses import dataclass

from bashful.agents import AgentInfo, load_agents
from bashful.discovery import check_agent
from bashful.runner import RunResult, get_version, run_agent

PING_PROMPT = "Reply with exactly one word: PONG"


@dataclass(frozen=True)
class HealthReport:
    agent_id: str
    name: str
    installed: bool
    path: str | None
    version: str | None
    ping_ok: bool | None  # None = not attempted
    ping_result: RunResult | None = None

    @property
    def status(self) -> str:
        if not self.installed:
            return "not installed"
        if self.ping_ok is None:
            return "installed"
        if self.ping_ok:
            return "healthy"
        return "unhealthy"


def check_health(
    agent: AgentInfo,
    *,
    ping: bool = False,
    timeout: float = 30.0,
) -> HealthReport:
    """Check an agent's health: install status, version, and optional live ping."""
    disc = check_agent(agent)
    version = get_version(agent) if disc.installed else None

    ping_ok = None
    ping_result = None
    if ping and disc.installed and agent.headless is not None:
        try:
            ping_result = run_agent(agent, PING_PROMPT, timeout=timeout)
            # Consider it healthy if it exits 0 and produces any stdout
            ping_ok = ping_result.ok and bool(ping_result.stdout.strip())
        except ValueError:
            ping_ok = False

    return HealthReport(
        agent_id=agent.id,
        name=agent.name,
        installed=disc.installed,
        path=disc.path,
        version=version,
        ping_ok=ping_ok,
        ping_result=ping_result,
    )


def check_all_health(*, ping: bool = False, timeout: float = 30.0) -> list[HealthReport]:
    """Run health checks on all cataloged agents."""
    return [check_health(a, ping=ping, timeout=timeout) for a in load_agents()]
