# Bashful Review and Dialectic Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add simple but useful `review` and `dialectic` commands to Bashful, and make write-mode support easier to understand and configure without making the system heavyweight.

**Architecture:** Build both commands on top of existing compare/fanout/runner primitives. `review` should be an opinionated wrapper for critique-oriented prompts and optional judge synthesis. `dialectic` should be a lightweight thesis/antithesis/synthesis workflow rather than a complex debate framework. Add a small configuration layer for capability overrides so Bashful is less hard-coded about which agents can use which modes.

**Tech Stack:** Python 3.11+, stdlib only, pytest, existing Bashful package.

---

### Task 1: Add capability/config override support

**Objective:** Make write-mode support and agent capabilities simpler and more configurable.

**Files:**
- Create: `bashful/config.py`
- Modify: `bashful/agents.py`
- Modify: `bashful/data/agents.json`
- Modify: `bashful/cli.py`
- Test: `tests/test_config.py`
- Update: `tests/test_cli.py`
- Update: `tests/test_runner.py`

**Requirements:**
- Add a simple user config file under `~/.bashful/config.json`.
- Allow per-agent overrides for capabilities or modes.
- Keep the built-in catalog as the default, but merge user overrides on load.
- Do not add a huge config system; just enough to let users widen or narrow mode support intentionally.
- Add a command like `bashful config show` for visibility if practical.

### Task 2: Add review command

**Objective:** Make Bashful good at review-style workflows without requiring the user to handcraft compare prompts every time.

**Files:**
- Create: `bashful/review.py`
- Modify: `bashful/cli.py`
- Modify: `bashful/skill.py`
- Modify: `README.md`
- Test: `tests/test_review.py`
- Update: `tests/test_cli.py`

**Requirements:**
- Add `bashful review <agents> "target or prompt"`.
- It should use a review-oriented wrapper prompt while remaining transparent.
- Support optional `--judge <agent>`.
- Output should clearly separate reviewer outputs and synthesis.
- Keep scope modest: this is structured prompting + comparison, not a full PR integration system.

### Task 3: Add dialectic command

**Objective:** Add a simple thesis/antithesis/synthesis style command.

**Files:**
- Create: `bashful/dialectic.py`
- Modify: `bashful/cli.py`
- Modify: `bashful/skill.py`
- Modify: `README.md`
- Test: `tests/test_dialectic.py`
- Update: `tests/test_cli.py`

**Requirements:**
- Add `bashful dialectic <agent_a>,<agent_b> "question"`.
- Generate:
  - thesis response
  - antithesis response
  - optional synthesis via `--judge`
- Keep it lightweight and operational, not academic.
- Make output readable and artifact-friendly.

### Task 4: Hermes /bashful skill refresh

**Objective:** Make the Hermes Bashful skill reflect review/dialectic usage.

**Files:**
- Update local Hermes skill content for `bashful`
- Modify: `bashful/skill.py`
- Optionally update: `docs/hermes-profile.md`
- Test: `tests/test_skill.py`

**Requirements:**
- Document `review` and `dialectic`.
- Explain how Hermes should use them:
  - `review` for critique and code/doc/plan inspection
  - `dialectic` for exploring opposed strategies or tradeoffs
- Keep the skill practical and not too long.

## Verification

Run:
- `python -m pytest -q`
- `python -m bashful review claude,codex "Review this plan for risks."`
- `python -m bashful review claude,codex "Review this plan for risks." --judge claude`
- `python -m bashful dialectic claude,codex "Should this tool prefer local-first routing?"`
- `python -m bashful dialectic claude,codex "Should this tool prefer local-first routing?" --judge claude`

Expected:
- tests pass
- review output is clear and useful
- dialectic output is clear and synthesis-capable
- config override path is simple and inspectable
