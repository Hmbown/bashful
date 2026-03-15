# Bashful

Bash-native agent CLI discovery and orchestration toolkit.

Bashful is the process-centric substrate for managing agent CLIs on a developer machine. It discovers, catalogs, and provides a unified interface to agent tools like **Claude**, **Codex**, **Copilot**, **Gemini**, **Qwen**, and **OpenCode** — without replacing any of them.

> **How is this different from ACZ?** ACZ is a protocol-level bridge that connects running agents via MCP. Bashful operates one layer below: it manages the agent *binaries* themselves — detecting what's installed, launching processes, and supervising sessions. The two are complementary.

## Install

```bash
pip install -e .
```

## Usage

### Discovery

```bash
bashful list                # List all agents and install status
bashful doctor              # Readiness report
bashful show claude         # Details for a specific agent (includes modes)
bashful versions            # Version info for all installed agents
```

### Running agents

```bash
# One-shot headless prompt (blocking, default read mode)
bashful run gemini "What is the capital of France?"
bashful run codex "Fix the type error in main.py" -v
bashful run claude "Explain this function" -t 30 -o json

# Explicit write mode (agent must support it)
bashful run claude "Fix the bug in auth.py" -m write
bashful run codex "Add tests for utils.py" -m write
```

### Multi-agent fanout

```bash
# Sequential (default)
bashful fanout claude,codex,gemini "What's the best way to handle errors in Go?"

# Parallel — all agents run concurrently
bashful fanout claude,codex,gemini "What's the best way to handle errors in Go?" --parallel

# With timeout and mode
bashful fanout claude,codex "Add a docstring to main()" -m write -t 120
```

### Artifacts

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

### Health checks

```bash
bashful ping                # Quick check (install + version)
bashful ping --live         # Live check (sends a test prompt)
bashful ping gemini --live -v
```

### Background jobs (process supervision)

```bash
bashful launch claude "Refactor the auth module"
bashful launch claude "Fix the auth bug" -m write  # write mode
bashful jobs                # List all jobs
bashful jobs --running      # Only running jobs
bashful logs <job_id>       # Read stdout
bashful logs <job_id> --stderr --tail 20
bashful kill <job_id>       # Kill a running job
```

### Worktree isolation

```bash
bashful worktree create fix-auth          # Create isolated worktree
bashful worktree create add-tests --base main
bashful worktree list                     # List active worktrees
bashful worktree remove fix-auth          # Clean up

# Launch with automatic worktree isolation
bashful launch claude "Fix the auth bug" --isolate
```

### Skill document

```bash
# Print the full skill document (for piping into other agents)
bashful skill

# Include live system state
bashful skill --live

# Machine-readable metadata
bashful skill --json
```

## Execution modes

Bashful supports execution modes as a signal of intent.  Modes map to
**agent-specific CLI flags** (e.g. `--allowedTools` for Claude,
`--approval-policy` for Codex) but bashful itself does not sandbox the agent —
enforcement depends on each agent's own CLI behaviour.

| Mode | Description |
|------|-------------|
| `read` | Default. Signals a read-only query. No write-enabling flags are passed. |
| `write` | Signals that the agent should modify files. Agent-specific write flags are appended. Must be explicitly requested via `-m write`. |

Not all agents support `write` mode. Use `bashful show <agent>` to check.

## Supported agents

| Agent | Executable | Headless mode | Modes |
|-------|-----------|--------------|-------|
| Claude Code | `claude` | `claude -p "prompt"` | read, write |
| OpenAI Codex | `codex` | `codex exec "prompt"` | read, write |
| GitHub Copilot | `gh copilot` | `gh copilot -p "prompt" --allow-all-tools` | read |
| Gemini CLI | `gemini` | `gemini -p "prompt" -o text` | read |
| Qwen CLI | `qwen` | `qwen -p "prompt" -o text` | read |
| OpenCode | `opencode` | `opencode run "prompt"` | read |

## Architecture

- **Agent catalog** (`bashful/data/agents.json`) — machine-readable inventory with headless invocation profiles and per-agent execution modes
- **Discovery** (`bashful/discovery.py`) — detects installed agents via `shutil.which`
- **Runner** (`bashful/runner.py`) — runs agents as subprocesses with timeout/capture and mode support
- **Fanout** (`bashful/fanout.py`) — multi-agent fanout (sequential or parallel) for running the same prompt across agents
- **Artifacts** (`bashful/artifacts.py`) — lightweight JSON artifact persistence for run/fanout results
- **Health** (`bashful/health.py`) — version + live ping checks
- **Supervisor** (`bashful/supervisor.py`) — background job management with file-based state
- **Worktree** (`bashful/worktree.py`) — git worktree isolation for parallel work
- **Skill** (`bashful/skill.py`) — generates a skill document teaching other agents how to use bashful
- **CLI** (`bashful/cli.py`) — unified command interface
