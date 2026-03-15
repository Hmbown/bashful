# Bashful Next Slice Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extend Bashful so it can better support real agent operations by adding write-capable execution profiles, multi-agent fanout, and stronger Hermes-facing skill output.

**Architecture:** Keep Bashful bootstrap-sized. Add a small execution-mode abstraction to the agent catalog and runner so agents can be invoked in read-only or write-capable mode when supported. Add one simple fanout command that runs the same prompt across multiple agents and returns grouped results. Improve the skill generator so Hermes gets a sharper, more operational document describing available agents, modes, and commands.

**Tech Stack:** Python 3.11+, stdlib, pytest, existing Bashful package structure.

---

### Task 1: Add execution modes to the agent catalog and runner

**Objective:** Support at least `read` and `write` execution modes for agents that can safely expose them.

**Files:**
- Modify: `bashful/agents.py`
- Modify: `bashful/data/agents.json`
- Modify: `bashful/runner.py`
- Modify: `bashful/supervisor.py`
- Modify: `bashful/cli.py`
- Test: `tests/test_runner.py`
- Test: `tests/test_cli.py`

**Requirements:**
- Add a small catalog abstraction for per-agent execution modes.
- `bashful run` and `bashful launch` should accept `--mode`, defaulting to `read`.
- For Claude, add a write-capable mode using the appropriate auto-approval flag so Bashful can actually perform write tasks noninteractively when explicitly requested.
- Keep unsupported modes safe: raise a clear error instead of guessing.
- Do not invent broad unsafe defaults; write mode must be explicit.

### Task 2: Add multi-agent fanout command

**Objective:** Let Bashful run the same prompt across multiple agents in one command.

**Files:**
- Modify: `bashful/cli.py`
- Create or modify: `bashful/fanout.py`
- Modify: `bashful/runner.py` if needed
- Test: `tests/test_cli.py`
- Test: `tests/test_runner.py` or `tests/test_fanout.py`

**Requirements:**
- Add a command like `bashful fanout claude,codex,gemini "prompt"`.
- Run agents sequentially at first (keep scope modest) and print clearly separated outputs.
- Include per-agent success/failure markers.
- Reuse the existing runner where possible.
- Support `--mode`, `--timeout`, and `--output-format` if practical.

### Task 3: Improve Hermes-facing skill output

**Objective:** Make Bashful more useful as a substrate that Hermes can load or reference.

**Files:**
- Modify: `bashful/skill.py`
- Modify: `README.md`
- Test: `tests/test_skill.py`

**Requirements:**
- Update the generated skill document to explain execution modes and the new fanout command.
- Make the skill document more explicit about when to use Bashful versus ACZ.
- Add a machine-readable field or metadata entry if helpful, but keep it simple.
- Do not build a whole Hermes integration system yet; focus on a better exported skill document.

### Task 4: Verify with real Claude where safe

**Objective:** Prove the write-mode design works in practice for Claude without expanding scope too far.

**Files:**
- No new source files required unless needed for docs/tests
- Update docs/tests as needed

**Requirements:**
- Add at least one test covering mode selection.
- Ensure the code path for Claude write mode is explicit and inspectable.
- Keep the overall repo clean, tested, and public-safe.

## Verification

Run:
- `python -m pytest -q`
- `python -m bashful doctor`
- `python -m bashful show claude`
- `python -m bashful fanout claude,codex "Reply with READY only."` (or equivalent if implemented slightly differently)

Expected:
- tests pass
- CLI help and commands remain coherent
- unsupported mode errors are clear
- fanout output is readable
