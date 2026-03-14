"""Skill document generator — teaches other agents how to use bashful."""

from __future__ import annotations

from bashful import __version__
from bashful.agents import load_agents


def generate_skill_doc(*, include_state: bool = False) -> str:
    """Generate the bashful skill document.

    Args:
        include_state: If True, include live system state (installed agents,
            running jobs, active worktrees).
    """
    agents = load_agents()

    # Build agents table
    agent_rows = []
    for a in agents:
        headless = a.invocation if a.headless else "(interactive only)"
        agent_rows.append(f"| {a.name} | `{a.executable}` | `{headless}` |")
    agents_table = "\n".join(agent_rows)

    doc = _TEMPLATE.format(
        version=__version__,
        agents_table=agents_table,
        live_state=_build_live_state() if include_state else "",
    )

    return doc.strip() + "\n"


def _build_live_state() -> str:
    """Build the live state section by querying bashful's own modules."""
    sections = []

    # Installed agents
    try:
        from bashful.discovery import discover
        results = discover()
        installed = [r for r in results if r.installed]
        missing = [r for r in results if not r.installed]
        lines = ["## Current State", ""]
        lines.append(f"**Installed agents:** {len(installed)}/{len(results)}")
        if installed:
            for r in installed:
                lines.append(f"- {r.id}: `{r.path}`")
        if missing:
            lines.append(f"\n**Missing:** {', '.join(r.id for r in missing)}")
        sections.append("\n".join(lines))
    except Exception:
        pass

    # Running jobs
    try:
        from bashful.supervisor import list_jobs
        jobs = list_jobs()
        if jobs:
            lines = ["", "**Active jobs:**"]
            for j in jobs:
                lines.append(f"- `{j.job_id}` ({j.agent_id}): {j.state}")
            sections.append("\n".join(lines))
    except Exception:
        pass

    # Active worktrees
    try:
        from bashful.worktree import list_worktrees
        wts = list_worktrees()
        if wts:
            lines = ["", "**Active worktrees:**"]
            for w in wts:
                lines.append(f"- `{w.name}` on `{w.branch}` at `{w.path}`")
            sections.append("\n".join(lines))
    except Exception:
        pass

    return "\n".join(sections)


def get_skill_metadata() -> dict:
    """Return structured metadata about bashful's capabilities."""
    agents = load_agents()
    return {
        "name": "bashful",
        "version": __version__,
        "description": "Bash-native agent CLI discovery and orchestration toolkit",
        "agents": [a.id for a in agents],
        "commands": [
            "list", "doctor", "show", "run", "ping", "versions",
            "launch", "jobs", "logs", "kill",
            "worktree create", "worktree list", "worktree remove",
            "skill",
        ],
    }


_TEMPLATE = """\
# Bashful — Agent CLI Toolkit

> Version {version} — bash-native agent CLI discovery and orchestration.

Bashful manages agent CLI binaries on the local machine. It discovers what's
installed, runs agents in headless mode, supervises background jobs, and
isolates work in git worktrees.

Use bashful when you need to:
- Find out which agent CLIs are available
- Dispatch a prompt to a specific agent
- Launch long-running agent work in the background
- Run agents in isolated git worktrees for parallel work

## Commands

| Command | Description |
|---------|-------------|
| `bashful list` | List all supported agents and install status |
| `bashful doctor` | Readiness report — what's installed, what's missing |
| `bashful show <agent>` | Show full details for a specific agent |
| `bashful versions [agent]` | Print version info for installed agents |
| `bashful ping [agent] [--live]` | Health check (version + optional API ping) |
| `bashful run <agent> "prompt"` | Run an agent with a prompt (headless, blocking) |
| `bashful launch <agent> "prompt"` | Launch a background job |
| `bashful jobs` | List all jobs and their status |
| `bashful logs <job_id>` | Read stdout/stderr from a job |
| `bashful kill <job_id>` | Kill a running job |
| `bashful worktree create <name>` | Create an isolated git worktree |
| `bashful worktree list` | List active worktrees |
| `bashful worktree remove <name>` | Remove a worktree |
| `bashful skill [--live]` | Print this skill document |

## Supported Agents

| Agent | Executable | Headless invocation |
|-------|-----------|---------------------|
{agents_table}

## Workflows

### 1. Discover what's available

```bash
bashful doctor
bashful versions
```

### 2. Run a one-shot prompt

```bash
bashful run gemini "Explain this error message"
bashful run codex "Write a Dockerfile for a Python Flask app" -o json
bashful run claude "Review this function for bugs" -v
```

### 3. Launch background work

```bash
# Start a job
bashful launch claude "Refactor the auth module"

# Check status
bashful jobs

# Read output
bashful logs <job_id>

# Cancel if needed
bashful kill <job_id>
```

### 4. Parallel work with worktree isolation

```bash
# Create isolated worktrees
bashful worktree create fix-auth
bashful worktree create add-tests

# Launch agents in isolation
bashful launch claude "Fix the auth bug" --isolate
bashful launch gemini "Add unit tests" --isolate

# Check everything
bashful jobs
bashful worktree list

# Clean up
bashful worktree remove fix-auth
bashful worktree remove add-tests
```

### 5. Multi-agent comparison

```bash
# Ask the same question to multiple agents
bashful run claude "What's the best way to handle errors in Go?"
bashful run gemini "What's the best way to handle errors in Go?"
bashful run codex "What's the best way to handle errors in Go?"
```

## Tips

- Use `bashful run` for quick, synchronous queries.
- Use `bashful launch` for work that takes more than a few seconds.
- Use `--isolate` with `launch` to prevent agents from conflicting.
- Use `bashful ping --live` to verify API connectivity before launching work.
- Logs persist in `~/.bashful/jobs/` — check old results anytime.
- Worktrees live as siblings of your repo in `.bashful-worktrees/`.

{live_state}
"""
