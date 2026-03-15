# Hermes Profile — Using Bashful as a Substrate

Bashful is a process-centric substrate for managing agent CLI binaries.
Hermes should treat it as a low-level tool for dispatching and supervising
agent processes, not as a replacement for ACZ-level orchestration.

## When to use Bashful

- **Discover available agents** — `bashful doctor` or `bashful list`
- **One-shot prompt** — `bashful run <agent> "prompt"` for a quick blocking call
- **Compare agents** — `bashful compare agent1,agent2 "prompt"` to run the same
  prompt across agents and see results side-by-side
- **Judge a comparison** — `bashful compare agent1,agent2 "prompt" --judge claude`
  to have a judge agent synthesize which response is best
- **Structured review** — `bashful review agent1,agent2 "target" --judge claude`
  for critique-oriented workflows (plan review, code audit, doc inspection).
  Each reviewer gets a review-focused prompt; `--judge` synthesizes findings.
- **Dialectic** — `bashful dialectic agent_a,agent_b "question" --judge claude`
  for exploring opposed strategies or tradeoffs. One agent argues thesis,
  the other antithesis; `--judge` produces a synthesis.
- **Background work** — `bashful launch <agent> "prompt"` for long tasks, then
  `bashful wait <job_id>` or `bashful watch <job_id>` to follow progress
- **Isolated parallel work** — `bashful launch <agent> "prompt" --isolate` to
  run agents in separate git worktrees
- **Config visibility** — `bashful config` to check which user overrides are active

## When to escalate to ACZ

- Durable multi-agent orchestration spanning sessions
- Protocol-level agent-to-agent communication (MCP bridging)
- Workflows requiring state machines, retry policies, or coordination primitives

## Recommended Hermes workflow

1. **Inspect** — `bashful doctor` to see what's installed
2. **Choose mode**:
   - Quick query → `bashful run`
   - Compare answers → `bashful compare`
   - Critique/review → `bashful review`
   - Explore tradeoffs → `bashful dialectic`
   - Long task → `bashful launch` + `bashful wait`/`bashful watch`
   - Parallel isolation → `bashful launch --isolate`
3. **Use Bashful for binary/process-level work** — starting, stopping,
   capturing output from agent CLIs
4. **Escalate to ACZ** only when durable orchestration is justified

## Key principles

- Bashful manages processes; ACZ manages protocols. They are complementary.
- Default execution mode is `read`. Use `-m write` only when the agent should
  modify files.
- `compare --judge` is lightweight — it runs a second agent with a transparent
  prompt. It is not a voting system or consensus mechanism.
- `review` is structured prompting + comparison — not a full PR integration system.
  Use it for inspecting plans, code, and documents.
- `dialectic` is a lightweight thesis/antithesis/synthesis pattern — not an
  academic debate framework. Use it to quickly surface opposing views.
- `wait` and `watch` are simple poll loops, not daemons. They are safe to
  interrupt with Ctrl-C.
- User overrides in `~/.bashful/config.json` can widen or narrow agent capabilities
  (e.g. enabling write mode for an agent that defaults to read-only).
