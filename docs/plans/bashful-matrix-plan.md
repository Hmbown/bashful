# Bashful Matrix and Artifact Tightening Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a clean `matrix` command for prompt-by-agent sweeps and tighten artifact support for higher-level commands without bloating Bashful.

**Architecture:** Reuse the existing runner, fanout, compare, review, dialectic, normalize, and artifacts modules. `matrix` should be a small wrapper that runs a list of prompts across a list of agents and returns readable grouped output plus a structured artifact when requested. Artifact support for `review` and `dialectic` should follow the same explicit save pattern already used elsewhere.

**Tech Stack:** Python 3.11+, stdlib only, pytest, existing Bashful package.

---

### Task 1: Add matrix command

**Objective:** Run multiple prompts across multiple agents in a small, understandable way.

**Files:**
- Create: `bashful/matrix.py`
- Modify: `bashful/cli.py`
- Modify: `bashful/skill.py`
- Modify: `README.md`
- Test: `tests/test_matrix.py`
- Update: `tests/test_cli.py`

**Requirements:**
- Add `bashful matrix <agents> --prompt "..." --prompt "..."`.
- Allow at least two prompts and one or more agents.
- Sequential execution is fine; optional `--parallel` is okay only if it stays simple.
- Output should be grouped by prompt and agent.
- Reuse existing fanout/runner logic where practical.
- Keep the interface minimal and obvious.

### Task 2: Add artifact save support for review and dialectic

**Objective:** Make higher-level flows artifact-friendly.

**Files:**
- Modify: `bashful/review.py`
- Modify: `bashful/dialectic.py`
- Modify: `bashful/artifacts.py`
- Modify: `bashful/cli.py`
- Test: `tests/test_review.py`
- Test: `tests/test_dialectic.py`
- Test: `tests/test_artifacts.py`

**Requirements:**
- Add `--save` to `bashful review` and `bashful dialectic`.
- Save enough structure to reconstruct what happened later.
- Keep artifact schema simple and consistent with existing patterns.

### Task 3: Keep output and docs clean

**Objective:** Prevent feature creep and keep Bashful readable.

**Files:**
- Modify: `README.md`
- Modify: `bashful/skill.py`
- Optionally update: `docs/hermes-profile.md`
- Test: `tests/test_skill.py`

**Requirements:**
- Document matrix briefly.
- Document save support for review/dialectic.
- Do not add unnecessary abstractions or a second config system.

## Verification

Run:
- `python -m pytest -q`
- `python -m bashful matrix claude,codex --prompt "Reply with READY only." --prompt "Reply with OK only."`
- `python -m bashful review claude,codex "Review this plan for risks." --save`
- `python -m bashful dialectic claude,codex "Should this tool prefer local-first routing?" --judge claude --save`

Expected:
- tests pass
- matrix output is readable and artifact-friendly
- review/dialectic save flows work cleanly
- docs stay compact
