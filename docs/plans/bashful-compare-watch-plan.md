# Bashful Compare, Watch, and Hermes Profile Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Extend Bashful with structured output normalization, compare/judge mode, better long-job ergonomics, and a clearer Hermes-native profile without turning Bashful into a full orchestration platform.

**Architecture:** Keep Bashful process-centric. Add a lightweight normalization layer that can summarize run/fanout results into a stable schema. Build compare mode on top of fanout plus an optional judge pass. Add minimal job ergonomics (`wait` and `watch`) on top of the existing supervisor instead of inventing a daemon. Add a Hermes-facing profile document/template that teaches Hermes how to use Bashful as a low-level substrate.

**Tech Stack:** Python 3.11+, stdlib only, pytest, existing Bashful package structure.

---

### Task 1: Add structured normalization helpers

**Objective:** Normalize run and fanout results into a consistent machine-readable summary.

**Files:**
- Create: `bashful/normalize.py`
- Modify: `bashful/runner.py`
- Modify: `bashful/fanout.py`
- Modify: `bashful/artifacts.py`
- Test: `tests/test_normalize.py`
- Update: `tests/test_runner.py`
- Update: `tests/test_fanout.py`

**Requirements:**
- Add a small normalization layer that can summarize:
  - run result -> `{agent, ok, timed_out, exit_code, stdout_preview, stderr_preview, mode, duration_s}`
  - fanout result -> list of normalized per-agent items plus overall success/failure
- Avoid over-parsing model content; keep this structural.
- Use the normalization helpers in artifacts where useful.
- Keep it optional and lightweight.

### Task 2: Add compare/judge mode

**Objective:** Let Bashful run several agents and optionally ask a judge agent to synthesize the comparison.

**Files:**
- Modify: `bashful/cli.py`
- Create or modify: `bashful/compare.py`
- Modify: `bashful/fanout.py` if needed
- Test: `tests/test_compare.py`
- Update: `tests/test_cli.py`

**Requirements:**
- Add a command like `bashful compare claude,codex,gemini "prompt"`.
- The command should run fanout first.
- Add optional `--judge <agent>` to summarize outputs using a second agent.
- Judge prompt should be simple and transparent.
- Output should include raw per-agent results plus a judge section when requested.
- Keep compare sequential/parallel behavior aligned with fanout flags if practical.

### Task 3: Add long-job ergonomics

**Objective:** Make background jobs easier to supervise without adding a daemon.

**Files:**
- Modify: `bashful/cli.py`
- Modify: `bashful/supervisor.py`
- Test: `tests/test_supervisor.py`
- Update: `README.md`

**Requirements:**
- Add `bashful wait <job_id>` to block until a job finishes and then print status.
- Add `bashful watch <job_id>` for simple polling output until completion.
- Keep implementation simple (poll loop + sleep).
- Do not introduce a service process.

### Task 4: Add Hermes-native profile material

**Objective:** Make it easier for Hermes to treat Bashful as a known low-level substrate.

**Files:**
- Modify: `bashful/skill.py`
- Modify: `README.md`
- Create: `docs/hermes-profile.md`
- Test: `tests/test_skill.py`

**Requirements:**
- Add a short Hermes profile doc explaining when Hermes should prefer Bashful vs ACZ.
- Update generated skill output to mention compare/judge mode and wait/watch.
- Include a concise recommended Hermes workflow:
  - inspect available agents
  - choose one-shot run vs launch vs fanout vs compare
  - use Bashful for binary/process-level work
  - escalate to ACZ only when durable orchestration is justified

## Verification

Run:
- `python -m pytest -q`
- `python -m bashful compare claude,codex "Reply with READY only."`
- `python -m bashful compare claude,codex "Reply with READY only." --judge claude`
- `python -m bashful launch claude "Reply with DONE only."`
- `python -m bashful wait <job_id>`

Expected:
- tests pass
- compare works without and with judge
- wait/watch are usable
- docs and skill output clearly explain Hermes usage
