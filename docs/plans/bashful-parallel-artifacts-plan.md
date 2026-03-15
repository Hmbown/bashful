# Bashful Parallel Fanout and Artifact Capture Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make Bashful more useful for real multi-agent supervision by adding artifact persistence and optional parallel fanout while keeping the interface small and readable.

**Architecture:** Reuse the existing runner and fanout modules. Add a lightweight artifact layer that stores one-shot run/fanout results under `~/.bashful/artifacts/` as JSON files with timestamps and metadata. Extend fanout to support `--parallel` execution using a modest thread pool. Expose a small CLI surface for saving outputs and inspecting recent artifacts.

**Tech Stack:** Python 3.11+, stdlib only, pytest, existing Bashful package.

---

### Task 1: Add artifact persistence for run and fanout

**Objective:** Save reproducible JSON artifacts for one-shot runs and fanouts.

**Files:**
- Create: `bashful/artifacts.py`
- Modify: `bashful/runner.py`
- Modify: `bashful/fanout.py`
- Modify: `bashful/cli.py`
- Test: `tests/test_artifacts.py`
- Update: `tests/test_runner.py`
- Update: `tests/test_fanout.py`

**Requirements:**
- Add a simple artifact directory under `~/.bashful/artifacts/`.
- Persist run metadata: agent, mode, prompt hash or prompt, command, stdout/stderr, exit_code, timed_out, duration, cwd, timestamp.
- Persist fanout metadata: agent list, mode, prompt, per-agent results, overall success/failure, timestamp.
- CLI should support an explicit `--save` flag for `run` and `fanout`.
- Keep default behavior unchanged unless `--save` is requested.
- Artifacts must be JSON and easy for Hermes or another tool to read later.

### Task 2: Add recent artifact inspection commands

**Objective:** Let users list and inspect saved artifacts.

**Files:**
- Modify: `bashful/cli.py`
- Update or create: `bashful/artifacts.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_artifacts.py`

**Requirements:**
- Add `bashful artifacts` to list recent saved artifacts.
- Add `bashful artifacts show <artifact_id>` to print a saved artifact.
- Keep the output simple and human-readable by default.
- JSON output is optional but nice if easy.

### Task 3: Add optional parallel fanout

**Objective:** Support concurrent fanout without making it the only behavior.

**Files:**
- Modify: `bashful/fanout.py`
- Modify: `bashful/cli.py`
- Test: `tests/test_fanout.py`

**Requirements:**
- Add a `parallel` option to fanout execution and a `--parallel` CLI flag.
- Keep sequential as the default for predictability.
- Use a small stdlib thread pool.
- Preserve per-agent result grouping and readable output.
- Handle partial failures cleanly.

### Task 4: Improve Hermes-facing skill output again

**Objective:** Reflect artifact support and parallel fanout in the skill doc.

**Files:**
- Modify: `bashful/skill.py`
- Modify: `README.md`
- Test: `tests/test_skill.py`

**Requirements:**
- Document artifact capture and inspection commands.
- Document sequential vs parallel fanout.
- Keep the skill document operational and concise.

## Verification

Run:
- `python -m pytest -q`
- `python -m bashful fanout claude,codex "Reply with READY only."`
- `python -m bashful fanout claude,codex "Reply with READY only." --parallel`
- `python -m bashful run claude "Reply with READY only." --save`
- `python -m bashful artifacts`

Expected:
- tests pass
- both sequential and parallel fanout work
- saved artifacts can be listed and inspected
- no change to default behavior unless `--save` or `--parallel` is explicitly requested
