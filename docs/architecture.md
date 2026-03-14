# Bashful Architecture

## Concept

Bashful treats agent CLIs as first-class Unix processes. Rather than wrapping them in an SDK or framework, Bashful discovers what's installed, describes how each tool should be invoked, and manages their lifecycle through standard process supervision.

## Components

- **Agent catalog** (`bashful/data/agents.json`) — machine-readable inventory of supported agent CLIs with headless invocation profiles, output format support, and version commands.
- **Discovery** (`bashful/discovery.py`) — uses `shutil.which` to detect installed agents and resolve paths. Supports subcommand-aware detection (e.g., `gh copilot`).
- **Runner** (`bashful/runner.py`) — runs agents as subprocesses in headless mode with timeout handling, stdout/stderr capture, and duration tracking.
- **Health** (`bashful/health.py`) — combines discovery, version lookup, and optional live ping into health reports.
- **Supervisor** (`bashful/supervisor.py`) — launches agent processes in the background, tracks them by job ID, polls status, and manages logs. State is persisted to `~/.bashful/jobs/` so jobs survive across bashful invocations.
- **Worktree** (`bashful/worktree.py`) — creates and manages git worktrees for isolated parallel agent work. Worktrees are placed as siblings of the repo under `.bashful-worktrees/` and tracked in `~/.bashful/worktrees.json`.
- **Skill** (`bashful/skill.py`) — generates a comprehensive skill document that teaches other AI agents how to use bashful. Can include live system state.
- **CLI** (`bashful/cli.py`) — human-readable and agent-friendly command interface.

## Design principles

1. **Stdlib first** — minimize dependencies; use Python's standard library for portability.
2. **Data-driven** — agent metadata lives in JSON, not code. Easy to extend without touching logic.
3. **No wrapping** — Bashful does not proxy or intercept agent I/O. It discovers, launches, and supervises.
4. **File-based state** — job metadata and worktree indexes are stored as JSON files. No database, no daemon.
5. **Small surface** — grow through iteration, not anticipation.

## Supervision model

```
bashful launch claude "fix auth"
    │
    ├── creates ~/.bashful/jobs/<id>/
    │   ├── meta.json      (agent, prompt, pid, command, cwd)
    │   ├── stdout.log     (subprocess stdout)
    │   ├── stderr.log     (subprocess stderr)
    │   └── status.json    (written on completion: state, exit_code, ended_at)
    │
    └── subprocess.Popen (detached via start_new_session=True)
```

In-session: Popen handles are kept in memory for fast polling.
Cross-session: PID liveness is checked via `os.kill(pid, 0)`.

## Worktree model

```
/repo/                          (main repository)
/repo/../.bashful-worktrees/    (sibling directory)
    ├── claude-fix-auth/        (isolated worktree)
    └── gemini-add-tests/       (isolated worktree)
```

Each worktree gets a `bashful/<name>` branch. Worktrees are not auto-removed when jobs finish — the user inspects, merges, and explicitly removes.
