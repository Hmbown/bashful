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
        modes = ", ".join(a.modes)
        agent_rows.append(f"| {a.name} | `{a.executable}` | `{headless}` | {modes} |")
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
        "agents": [
            {"id": a.id, "modes": a.modes} for a in agents
        ],
        "modes": ["read", "write"],
        "default_mode": "read",
        "commands": [
            "list", "doctor", "show", "run", "fanout", "compare",
            "review", "dialectic", "config",
            "ping", "versions",
            "launch", "jobs", "logs", "kill", "wait", "watch",
            "worktree create", "worktree list", "worktree remove",
            "artifacts", "artifacts show",
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
- Run the same prompt across multiple agents (fanout)
- Compare agent responses with an optional judge agent
- Get structured reviews/critiques from multiple agents
- Explore opposing strategies via thesis/antithesis dialectics
- Launch long-running agent work in the background
- Wait for or watch background jobs
- Run agents in isolated git worktrees for parallel work

**Bashful vs Superpowers / subagent-driven-development:** those are prompt-level
workflow styles for how an agent should split up work. Bashful operates at the
process layer: it manages the actual agent *binaries* on disk — detecting
what's installed, launching processes, supervising sessions, and capturing
artifacts.

**Bashful vs ACZ:** Bashful manages processes; ACZ manages protocols. Use
Bashful for binary/process-level work (running agents, comparing outputs,
supervising jobs). Escalate to ACZ when you need durable multi-session
orchestration, protocol-level agent communication, or coordination primitives.

## Execution Modes

Bashful supports execution modes as a signal of intent.  The default is always
`read`.  Modes map to **agent-specific CLI flags** (e.g. `--allowedTools` for
Claude, `--approval-policy` for Codex) but bashful itself does not sandbox the
agent — enforcement depends on each agent's own CLI behaviour.

| Mode | Description |
|------|-------------|
| `read` | Default. Signals a read-only query. No write-enabling flags are passed. |
| `write` | Signals that the agent should be allowed to modify files. Agent-specific write flags are appended. Must be explicitly requested. |

Not all agents support `write` mode.  Requesting an unsupported mode produces a
clear error.  Use `bashful show <agent>` to check which modes an agent supports.

## Commands

| Command | Description |
|---------|-------------|
| `bashful list` | List all supported agents and install status |
| `bashful doctor` | Readiness report — what's installed, what's missing |
| `bashful show <agent>` | Show full details for a specific agent |
| `bashful versions [agent]` | Print version info for installed agents |
| `bashful ping [agent] [--live]` | Health check (version + optional API ping) |
| `bashful run <agent> "prompt" [-m mode]` | Run an agent with a prompt (headless, blocking) |
| `bashful fanout agent1,agent2 "prompt"` | Run the same prompt across multiple agents (sequential) |
| `bashful fanout agent1,agent2 "prompt" --parallel` | Run fanout concurrently |
| `bashful compare agent1,agent2 "prompt"` | Compare responses side-by-side |
| `bashful compare agent1,agent2 "prompt" --judge claude` | Compare with a judge agent |
| `bashful review agent1,agent2 "target"` | Structured review/critique from multiple agents |
| `bashful review agent1,agent2 "target" --judge claude` | Review with synthesized assessment |
| `bashful dialectic agent_a,agent_b "question"` | Thesis/antithesis dialectic |
| `bashful dialectic agent_a,agent_b "question" --judge claude` | Dialectic with synthesis |
| `bashful config` | Show current configuration and overrides |
| `bashful launch <agent> "prompt" [-m mode]` | Launch a background job |
| `bashful jobs` | List all jobs and their status |
| `bashful logs <job_id>` | Read stdout/stderr from a job |
| `bashful kill <job_id>` | Kill a running job |
| `bashful wait <job_id>` | Block until a job finishes |
| `bashful watch <job_id>` | Stream job output until completion |
| `bashful worktree create <name>` | Create an isolated git worktree |
| `bashful worktree list` | List active worktrees |
| `bashful worktree remove <name>` | Remove a worktree |
| `bashful run <agent> "prompt" --save` | Run and save an artifact |
| `bashful fanout agents "prompt" --save` | Fanout and save an artifact |
| `bashful artifacts` | List saved artifacts |
| `bashful artifacts <id>` | Show a saved artifact (JSON) |
| `bashful skill [--live]` | Print this skill document |

## Supported Agents

| Agent | Executable | Headless invocation | Modes |
|-------|-----------|---------------------|-------|
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
bashful run codex "Write a Dockerfile for a Python Flask app"
bashful run claude "Review this function for bugs" -v
```

### 3. Run with write mode (explicit opt-in)

```bash
bashful run claude "Fix the type error in main.py" -m write
bashful run codex "Add unit tests for auth.py" -m write
```

### 4. Multi-agent fanout

```bash
# Sequential (default) — predictable, one at a time
bashful fanout claude,codex,gemini "What's the best way to handle errors in Go?"

# Parallel — all agents run concurrently
bashful fanout claude,codex,gemini "What's the best way to handle errors in Go?" --parallel

# Fanout with write mode
bashful fanout claude,codex "Add a docstring to main()" -m write
```

### 5. Compare agent responses

```bash
# Compare two agents side-by-side
bashful compare claude,codex "Explain this error"

# Compare with a judge agent to synthesize
bashful compare claude,codex,gemini "Best way to handle errors?" --judge claude

# Parallel comparison
bashful compare claude,codex "Review this code" --parallel
```

### 6. Structured review

```bash
# Get critique from multiple agents
bashful review claude,codex "Review this plan for risks."

# Synthesize reviews with a judge
bashful review claude,codex "Review this plan for risks." --judge claude

# Parallel reviews
bashful review claude,codex,gemini "Audit this code for security" --parallel
```

### 7. Dialectic (thesis / antithesis / synthesis)

```bash
# Two agents argue opposing sides
bashful dialectic claude,codex "Should this tool prefer local-first routing?"

# Add synthesis via a judge
bashful dialectic claude,codex "Should we use a monorepo?" --judge claude
```

### 8. Save and inspect artifacts

```bash
# Save a run result
bashful run claude "Explain this function" --save

# Save a fanout result
bashful fanout claude,codex "Review this code" --save

# List recent artifacts
bashful artifacts

# Show a specific artifact (JSON)
bashful artifacts run-claude-1710000000
```

Artifacts are stored as JSON in `~/.bashful/artifacts/` and can be read by
other tools (e.g. Hermes) for post-hoc analysis.

### 9. Launch background work

```bash
# Start a job
bashful launch claude "Refactor the auth module"

# Start a write-mode job
bashful launch claude "Refactor the auth module" -m write

# Check status
bashful jobs

# Read output
bashful logs <job_id>

# Wait for completion (blocks until done)
bashful wait <job_id>

# Watch live output (streams stdout until done)
bashful watch <job_id>

# Cancel if needed
bashful kill <job_id>
```

### 10. Parallel work with worktree isolation

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

## Tips

- Use `bashful run` for quick, synchronous queries.
- Use `bashful compare` to compare agent responses with an optional `--judge`.
- Use `bashful review` for critique-oriented workflows (plan/code/doc inspection).
- Use `bashful dialectic` to explore opposing strategies or tradeoffs.
- Use `bashful fanout` for multi-agent dispatch without judge overhead (`--parallel` for speed).
- Use `--save` with `run` or `fanout` to persist results as artifacts.
- Use `bashful launch` for work that takes more than a few seconds; follow with `wait` or `watch`.
- Use `--isolate` with `launch` to prevent agents from conflicting.
- Use `-m write` only when you need the agent to modify files.
- Use `bashful ping --live` to verify API connectivity before launching work.
- Logs persist in `~/.bashful/jobs/` — check old results anytime.
- Worktrees live as siblings of your repo in `.bashful-worktrees/`.
- **Privacy:** Saved artifacts (`--save`) store the full prompt and agent output
  as plaintext JSON. These may contain sensitive instructions or model responses.
  Treat `~/.bashful/artifacts/` with the same care as shell history.

{live_state}
"""
