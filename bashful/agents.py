"""Agent catalog loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).parent / "data" / "agents.json"


@dataclass(frozen=True)
class HeadlessProfile:
    """How to invoke an agent in non-interactive (headless) mode."""

    style: str  # "flag" or "subcommand"
    args: list[str] = field(default_factory=list)
    output_format_flag: str | None = None
    output_formats: list[str] = field(default_factory=list)

    def build_command(
        self,
        executable: str,
        prompt: str,
        output_format: str | None = None,
    ) -> list[str]:
        """Build the full command list for a headless invocation."""
        cmd = [executable]
        for arg in self.args:
            cmd.append(arg.replace("{prompt}", prompt))
        if output_format and self.output_format_flag and output_format in self.output_formats:
            # Replace existing output format args if already present
            if self.output_format_flag in cmd:
                idx = cmd.index(self.output_format_flag)
                cmd[idx + 1] = output_format
            else:
                cmd.extend([self.output_format_flag, output_format])
        return cmd


@dataclass(frozen=True)
class AgentInfo:
    id: str
    name: str
    executable: str
    description: str
    invocation: str
    subcommand: str | None = None
    headless: HeadlessProfile | None = None
    version_args: list[str] = field(default_factory=list)


def _parse_headless(raw: dict[str, Any] | None) -> HeadlessProfile | None:
    if raw is None:
        return None
    return HeadlessProfile(
        style=raw["style"],
        args=raw.get("args", []),
        output_format_flag=raw.get("output_format_flag"),
        output_formats=raw.get("output_formats", []),
    )


def load_agents() -> list[AgentInfo]:
    """Load the agent catalog from the bundled JSON file."""
    with open(DATA_FILE) as f:
        raw = json.load(f)
    agents = []
    for entry in raw:
        headless = _parse_headless(entry.pop("headless", None))
        version_args = entry.pop("version_args", [])
        agents.append(AgentInfo(**entry, headless=headless, version_args=version_args))
    return agents


def get_agent(agent_id: str) -> AgentInfo | None:
    """Look up a single agent by id."""
    for agent in load_agents():
        if agent.id == agent_id:
            return agent
    return None
