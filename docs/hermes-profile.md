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
- **Background work** — `bashful launch <agent> "prompt"` for long tasks, then
  `bashful wait <job_id>` or `bashful watch <job_id>` to follow progress
- **Isolated parallel work** — `bashful launch <agent> "prompt" --isolate` to
  run agents in separate git worktrees

## When to escalate to ACZ

- Durable multi-agent orchestration spanning sessions
- Protocol-level agent-to-agent communication (MCP bridging)
- Workflows requiring state machines, retry policies, or coordination primitives

## Recommended Hermes workflow

1. **Inspect** — `bashful doctor` to see what's installed
2. **Choose mode**:
   - Quick query → `bashful run`
   - Compare answers → `bashful compare`
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
- `wait` and `watch` are simple poll loops, not daemons. They are safe to
  interrupt with Ctrl-C.
