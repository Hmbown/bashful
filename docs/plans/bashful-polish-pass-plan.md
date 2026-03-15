# Bashful Polish Pass Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Tighten Bashful's consistency and usability with a small polish pass: better symmetry around artifact saving, lightweight JSON output for core inspection commands, and README cleanup so the public surface is coherent and easy to scan.

**Architecture:** Reuse the existing command structure. Avoid new conceptual surface area except where it improves consistency. Prefer small flags and output-format improvements over new subsystems.

**Tech Stack:** Python 3.11+, stdlib only, pytest, existing Bashful package.

---

### Task 1: Improve command/output consistency

**Objective:** Make the CLI feel more uniform without adding bloat.

**Files:**
- Modify: `bashful/cli.py`
- Update: `tests/test_cli.py`

**Requirements:**
- Add `--save` support to `bashful compare` for symmetry with review/dialectic/fanout.
- Add lightweight `--json` output support for at least:
  - `bashful doctor`
  - `bashful list`
  - `bashful jobs`
  - optionally `bashful artifacts`
- Keep human-readable output as the default.
- Do not invent a giant formatting system.

### Task 2: Tighten artifacts ergonomics

**Objective:** Make artifact behavior easier to use without overengineering.

**Files:**
- Modify: `bashful/artifacts.py`
- Modify: `bashful/cli.py`
- Update: `tests/test_artifacts.py`

**Requirements:**
- Ensure compare save uses a simple consistent artifact schema.
- If easy, add a tiny artifact summary helper used by `bashful artifacts`.
- Keep saved JSON straightforward and stable.

### Task 3: README cleanup and public surface review

**Objective:** Make the README easier to scan and more obviously coherent.

**Files:**
- Modify: `README.md`
- Modify: `bashful/skill.py`
- Optionally modify: `docs/hermes-profile.md`
- Update: `tests/test_skill.py`

**Requirements:**
- Refresh the README command examples so they reflect the current surface cleanly.
- Group commands in a tighter order: discovery, run, compare/review/dialectic, jobs, artifacts, config.
- Mention JSON output where supported.
- Avoid duplicate or stale examples.
- Keep the README concise enough to read quickly.

## Verification

Run:
- `python -m pytest -q`
- `python -m bashful doctor --json`
- `python -m bashful list --json`
- `python -m bashful jobs --json`
- `python -m bashful compare claude,codex "Reply with READY only." --save`

Expected:
- tests pass
- JSON output is valid and useful
- compare save works
- README reflects the real command surface
