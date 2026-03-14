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
bashful show claude         # Details for a specific agent
bashful versions            # Version info for all installed agents
```

### Running agents

```bash
# One-shot headless prompt (blocking)
bashful run gemini "What is the capital of France?"
bashful run codex "Fix the type error in main.py" -v
bashful run claude "Explain this function" -t 30 -o json
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

## Supported agents

| Agent | Executable | Headless mode |
|-------|-----------|--------------|
| Claude Code | `claude` | `claude -p "prompt"` |
| OpenAI Codex | `codex` | `codex exec "prompt"` |
| GitHub Copilot | `gh copilot` | `gh copilot -p "prompt" --allow-all-tools` |
| Gemini CLI | `gemini` | `gemini -p "prompt" -o text` |
| Qwen CLI | `qwen` | `qwen -p "prompt" -o text` |
| OpenCode | `opencode` | `opencode run "prompt"` |

## Architecture

- **Agent catalog** (`bashful/data/agents.json`) — machine-readable inventory with headless invocation profiles
- **Discovery** (`bashful/discovery.py`) — detects installed agents via `shutil.which`
- **Runner** (`bashful/runner.py`) — runs agents as subprocesses with timeout/capture
- **Health** (`bashful/health.py`) — version + live ping checks
- **Supervisor** (`bashful/supervisor.py`) — background job management with file-based state
- **Worktree** (`bashful/worktree.py`) — git worktree isolation for parallel work
- **Skill** (`bashful/skill.py`) — generates a skill document teaching other agents how to use bashful
- **CLI** (`bashful/cli.py`) — unified command interface
