# Bashful Bootstrap Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Create the first working Bashful repo as a bash/native-CLI oriented agent-operations toolkit that can discover installed agent CLIs, describe how to use them, and provide a minimal command-line interface for Bashful-driven orchestration.

**Architecture:** Bashful starts as a small Python package plus documentation. The package owns agent inventory and detection logic, while the docs define the product concept: Bashful is the bash/process-centric substrate for managing agent CLIs like Claude, Codex, Gemini, Qwen, Copilot, and OpenCode. The first slice should be small, testable, and useful immediately on a developer machine.

**Tech Stack:** Python 3.11+, pytest, standard library only where practical, markdown docs, optional console entrypoint.

---

### Task 1: Initialize repo scaffold and concept docs

**Objective:** Create a clean, minimal repository structure that explains what Bashful is and why it exists.

**Files:**
- Create: `README.md`
- Create: `pyproject.toml`
- Create: `bashful/__init__.py`
- Create: `docs/architecture.md`
- Create: `.gitignore`

**Requirements:**
- README explains Bashful as bash-native agent management, distinct from ACZ.
- README names the initial supported agent families: claude, codex, copilot, gemini, qwen, opencode.
- `pyproject.toml` defines an installable Python package and a console script named `bashful`.
- Keep the repo intentionally small and bootstrap-oriented.

### Task 2: Implement agent inventory and discovery

**Objective:** Add a machine-readable catalog of supported agent CLIs and Python logic that detects whether each one is installed locally.

**Files:**
- Create: `bashful/agents.py`
- Create: `bashful/discovery.py`
- Create: `bashful/data/agents.json`
- Modify: `bashful/__init__.py`

**Requirements:**
- Catalog includes: id, display name, executable name, short description, and example invocation style.
- Discovery returns at least: agent id, installed bool, resolved path if present.
- Prefer stdlib (`shutil.which`, `subprocess`) for portability.
- Do not assume every CLI is installed.

### Task 3: Add a minimal Bashful CLI

**Objective:** Provide a useful command-line interface that makes Bashful immediately usable.

**Files:**
- Create: `bashful/cli.py`
- Create: `bashful/__main__.py`

**Requirements:**
- `bashful list` prints supported agents and install status.
- `bashful doctor` prints a concise readiness summary.
- `bashful show <agent>` prints how Bashful thinks that agent should be invoked and what it is good for.
- Keep output human-readable and agent-friendly.

### Task 4: Test the bootstrap slice

**Objective:** Add tests so the initial Bashful slice is deterministic and safe to extend.

**Files:**
- Create: `tests/test_discovery.py`
- Create: `tests/test_cli.py`

**Requirements:**
- Test discovery behavior with mocked `shutil.which`.
- Test CLI subcommands at least for `list` and `show`.
- Avoid dependence on actual installed CLIs during tests.

### Task 5: Add usage examples and next-step framing

**Objective:** Make the repo legible as the start of a broader system.

**Files:**
- Modify: `README.md`
- Optionally create: `docs/roadmap.md`

**Requirements:**
- Include example Bashful commands.
- Include a short “What comes next” section mentioning process supervision, worktrees, logging, and multi-agent orchestration.
- Keep scope modest: this is bootstrap infrastructure, not the full end state.

## Verification

Run:
- `python -m pytest -q`
- `python -m bashful list`
- `python -m bashful doctor`

Expected:
- tests pass
- CLI runs cleanly even if some or most agents are not installed
- docs and package structure are coherent
