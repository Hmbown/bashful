# Bashful

Bash-native agent CLI discovery and orchestration toolkit.

Bashful is the process-centric substrate for managing agent CLIs on a developer machine. It discovers, catalogs, and provides a unified interface to agent tools like **Claude**, **Codex**, **Copilot**, **Gemini**, **Qwen**, and **OpenCode** — without replacing any of them.

> **How is this different from Superpowers / subagent-driven-development?** Superpowers-style workflows are prompt-level methodologies for how an agent should break work down. Bashful operates at the process layer: it manages the actual agent *binaries* on your machine — detecting what's installed, launching processes, supervising jobs, and capturing artifacts.

## Install

```bash
pip install -e .
```

## Usage

### Discovery

```bash
bashful list                # List all agents and install status
bashful list --json         # Machine-readable output
bashful doctor              # Readiness report
bashful doctor --json       # JSON readiness report
bashful show claude         # Details for a specific agent
bashful versions            # Version info for all installed agents
bashful ping [agent] --live # Health check with optional API ping
```

### Run

```bash
bashful run gemini "What is the capital of France?"
bashful run claude "Explain this function" -t 30 -v
bashful run claude "Fix the bug in auth.py" -m write   # explicit write mode
bashful run codex "Add tests for utils.py" --save      # save as artifact
```

### Compare / Review / Dialectic

```bash
# Compare responses side-by-side
bashful compare claude,codex "Explain this error"
bashful compare claude,codex "Best approach?" --judge claude --save

# Structured review with optional synthesis
bashful review claude,codex "Review this plan." --judge claude --save

# Thesis / antithesis / synthesis
bashful dialectic claude,codex "Should we use a monorepo?" --judge claude --save
```

All three accept `--parallel`, `--judge AGENT`, and `--save`.

### Multi-agent fanout

```bash
bashful fanout claude,codex,gemini "How to handle errors in Go?"
bashful fanout claude,codex,gemini "How to handle errors in Go?" --parallel
bashful fanout claude,codex "Add a docstring to main()" -m write --save
```

### Matrix (prompt x agent sweep)

```bash
bashful matrix claude,codex --prompt "Summarize this" --prompt "Find risks"
bashful matrix claude,codex --prompt "p1" --prompt "p2" --parallel --save
```

### Background jobs

```bash
bashful launch claude "Refactor the auth module"
bashful launch claude "Fix the auth bug" -m write --isolate  # worktree isolation
bashful jobs                # List all jobs
bashful jobs --json         # JSON output
bashful logs <job_id>       # Read stdout
bashful kill <job_id>       # Kill a running job
bashful wait <job_id>       # Block until done
bashful watch <job_id>      # Stream output until done
```

### Artifacts

```bash
bashful artifacts           # List recent artifacts
bashful artifacts --json    # JSON listing
bashful artifacts <id>      # Show a specific artifact (JSON)
```

Any command with `--save` (`run`, `fanout`, `compare`, `review`, `dialectic`, `matrix`) persists results to `~/.bashful/artifacts/`.

### Worktree isolation

```bash
bashful worktree create fix-auth          # Create isolated worktree
bashful worktree list                     # List active worktrees
bashful worktree remove fix-auth          # Clean up
```

### Configuration

```bash
bashful config              # Show current config and overrides
```

User overrides live in `~/.bashful/config.json`.

### Skill document

```bash
bashful skill               # Print skill doc (for piping into other agents)
bashful skill --live        # Include live system state
bashful skill --json        # Machine-readable metadata
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
- **Fanout** (`bashful/fanout.py`) — multi-agent fanout (sequential or parallel)
- **Compare** (`bashful/compare.py`) — compare mode with optional judge agent
- **Review** (`bashful/review.py`) — structured critique via multi-agent review with optional synthesis
- **Dialectic** (`bashful/dialectic.py`) — thesis/antithesis/synthesis workflow
- **Matrix** (`bashful/matrix.py`) — prompt x agent matrix sweep
- **Artifacts** (`bashful/artifacts.py`) — lightweight JSON artifact persistence
- **Health** (`bashful/health.py`) — version + live ping checks
- **Supervisor** (`bashful/supervisor.py`) — background job management with file-based state
- **Worktree** (`bashful/worktree.py`) — git worktree isolation for parallel work
- **Config** (`bashful/config.py`) — user configuration overrides for agent capabilities
- **Normalize** (`bashful/normalize.py`) — lightweight result normalization helpers
- **Skill** (`bashful/skill.py`) — generates a skill document teaching other agents how to use bashful
- **CLI** (`bashful/cli.py`) — unified command interface
