"""Bashful command-line interface."""

from __future__ import annotations

import argparse
import sys
import time

from bashful import __version__
from bashful.agents import DEFAULT_MODE, VALID_MODES, get_agent, load_agents
from bashful.discovery import check_agent, discover


# ---------------------------------------------------------------------------
# Discovery commands
# ---------------------------------------------------------------------------

def cmd_list(_args: argparse.Namespace) -> None:
    """Print all supported agents and their install status."""
    results = discover()
    for r in results:
        status = "installed" if r.installed else "not found"
        path_info = f"  ({r.path})" if r.path else ""
        print(f"  {r.id:<12} {r.name:<22} [{status}]{path_info}")


def cmd_doctor(_args: argparse.Namespace) -> None:
    """Print a readiness summary."""
    results = discover()
    found = [r for r in results if r.installed]
    missing = [r for r in results if not r.installed]
    print(f"bashful v{__version__} — agent readiness report\n")
    print(f"  {len(found)}/{len(results)} agent CLIs detected\n")
    if found:
        print("  Ready:")
        for r in found:
            print(f"    {r.id:<12} {r.path}")
    if missing:
        print("  Missing:")
        for r in missing:
            print(f"    {r.id}")
    print()


def cmd_show(args: argparse.Namespace) -> None:
    """Show details for a specific agent."""
    agent = get_agent(args.agent)
    if agent is None:
        known = ", ".join(a.id for a in load_agents())
        print(f"Unknown agent: {args.agent}")
        print(f"Known agents: {known}")
        sys.exit(1)
    result = check_agent(agent)
    status = "installed" if result.installed else "not found"
    print(f"  Agent:       {agent.name} ({agent.id})")
    print(f"  Executable:  {agent.executable} [{status}]")
    if result.path:
        print(f"  Path:        {result.path}")
    print(f"  Description: {agent.description}")
    print(f"  Invocation:  {agent.invocation}")
    print(f"  Modes:       {', '.join(agent.modes)}")
    if agent.headless:
        print(f"  Headless:    {agent.headless.style} mode")
        if agent.headless.output_formats:
            print(f"  Formats:     {', '.join(agent.headless.output_formats)}")


# ---------------------------------------------------------------------------
# Run command
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> None:
    """Run an agent CLI with a prompt in headless mode."""
    from bashful.runner import run_agent

    agent = get_agent(args.agent)
    if agent is None:
        known = ", ".join(a.id for a in load_agents())
        print(f"Unknown agent: {args.agent}", file=sys.stderr)
        print(f"Known agents: {known}", file=sys.stderr)
        sys.exit(1)

    prompt = " ".join(args.prompt)
    if not prompt:
        print("No prompt provided.", file=sys.stderr)
        sys.exit(1)

    try:
        result = run_agent(
            agent,
            prompt,
            timeout=args.timeout,
            output_format=args.output_format,
            mode=args.mode,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if result.stdout.strip():
        print(result.stdout.strip())

    if args.verbose:
        print(f"\n--- bashful run metadata ---", file=sys.stderr)
        print(f"  agent:     {result.agent_id}", file=sys.stderr)
        print(f"  mode:      {result.mode}", file=sys.stderr)
        print(f"  command:   {' '.join(result.command)}", file=sys.stderr)
        print(f"  exit_code: {result.exit_code}", file=sys.stderr)
        print(f"  duration:  {result.duration_s}s", file=sys.stderr)
        if result.timed_out:
            print(f"  TIMED OUT", file=sys.stderr)
        if result.stderr.strip():
            print(f"  stderr:    {result.stderr.strip()[:200]}", file=sys.stderr)

    if args.save:
        from bashful.artifacts import save_run_artifact
        artifact_id = save_run_artifact(result, prompt)
        print(f"  Saved artifact: {artifact_id}", file=sys.stderr)

    if not result.ok:
        sys.exit(result.exit_code if result.exit_code > 0 else 1)


# ---------------------------------------------------------------------------
# Fanout command
# ---------------------------------------------------------------------------

def cmd_fanout(args: argparse.Namespace) -> None:
    """Run the same prompt across multiple agents."""
    from bashful.fanout import fanout

    agent_ids = [a.strip() for a in args.agents.split(",") if a.strip()]
    if not agent_ids:
        print("No agents specified.", file=sys.stderr)
        sys.exit(1)

    prompt = " ".join(args.prompt)
    if not prompt:
        print("No prompt provided.", file=sys.stderr)
        sys.exit(1)

    results = fanout(
        agent_ids,
        prompt,
        timeout=args.timeout,
        output_format=args.output_format,
        mode=args.mode,
        parallel=args.parallel,
    )

    # Print results with clear separation
    from bashful.fanout import FanoutError

    any_failed = False
    for i, (agent_id, result) in enumerate(results):
        if i > 0:
            print()
        if result.ok:
            marker = "OK"
        elif result.timed_out:
            marker = "TIMEOUT"
            any_failed = True
        else:
            marker = f"FAIL(exit={result.exit_code})"
            any_failed = True
        print(f"--- {agent_id} [{marker}] ---")
        if isinstance(result, FanoutError):
            print(result.error)
        else:
            if result.stdout.strip():
                print(result.stdout.strip())
            if not result.ok and result.stderr.strip():
                print(f"  stderr: {result.stderr.strip()[:200]}", file=sys.stderr)

    if args.save:
        from bashful.artifacts import save_fanout_artifact
        artifact_id = save_fanout_artifact(results, prompt, mode=args.mode)
        print(f"\n  Saved artifact: {artifact_id}", file=sys.stderr)

    if any_failed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Compare command
# ---------------------------------------------------------------------------

def cmd_compare(args: argparse.Namespace) -> None:
    """Run agents and optionally judge the results."""
    from bashful.compare import compare

    agent_ids = [a.strip() for a in args.agents.split(",") if a.strip()]
    if not agent_ids:
        print("No agents specified.", file=sys.stderr)
        sys.exit(1)

    prompt = " ".join(args.prompt)
    if not prompt:
        print("No prompt provided.", file=sys.stderr)
        sys.exit(1)

    data = compare(
        agent_ids,
        prompt,
        timeout=args.timeout,
        output_format=args.output_format,
        mode=args.mode,
        parallel=args.parallel,
        judge=args.judge,
        judge_timeout=args.judge_timeout,
    )

    from bashful.fanout import FanoutError

    any_failed = False
    for i, (agent_id, result) in enumerate(data["results"]):
        if i > 0:
            print()
        if result.ok:
            marker = "OK"
        elif getattr(result, "timed_out", False):
            marker = "TIMEOUT"
            any_failed = True
        else:
            marker = f"FAIL(exit={result.exit_code})"
            any_failed = True
        print(f"--- {agent_id} [{marker}] ---")
        if isinstance(result, FanoutError):
            print(result.error)
        elif result.stdout.strip():
            print(result.stdout.strip())

    if data["judge"]:
        j = data["judge"]
        print(f"\n=== judge: {j['agent']} ===")
        if j["ok"]:
            print(j.get("stdout", ""))
        else:
            print(f"[judge error: {j.get('error', 'unknown')}]")

    if any_failed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Artifact commands
# ---------------------------------------------------------------------------

def cmd_artifacts(args: argparse.Namespace) -> None:
    """List or show saved artifacts."""
    positionals = args.artifact_args or []
    if not positionals:
        _list_artifacts()
    elif positionals[0] == "show":
        if len(positionals) != 2:
            print("Usage: bashful artifacts show <artifact_id>", file=sys.stderr)
            sys.exit(1)
        _show_artifact(positionals[1])
    elif len(positionals) == 1:
        _show_artifact(positionals[0])
    else:
        print("Usage: bashful artifacts [show] <artifact_id>", file=sys.stderr)
        sys.exit(1)


def _list_artifacts() -> None:
    from bashful.artifacts import list_artifacts
    import datetime

    arts = list_artifacts()
    if not arts:
        print("  No saved artifacts.")
        return

    for a in arts:
        ts = datetime.datetime.fromtimestamp(a["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        if a["type"] == "run":
            ok = "OK" if a["exit_code"] == 0 and not a["timed_out"] else "FAIL"
            print(f"  {a['id']:<40} {a['type']:<8} {a['agent']:<10} [{ok}]  {ts}")
        else:
            ok = "OK" if a.get("all_ok") else "FAIL"
            agents = ",".join(a.get("agents", []))
            print(f"  {a['id']:<40} {a['type']:<8} {agents:<10} [{ok}]  {ts}")


def _show_artifact(artifact_id: str) -> None:
    import json
    from bashful.artifacts import show_artifact

    data = show_artifact(artifact_id)
    if data is None:
        print(f"  Artifact not found: {artifact_id}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Health commands
# ---------------------------------------------------------------------------

def cmd_ping(args: argparse.Namespace) -> None:
    """Ping one or all agents to check health."""
    from bashful.health import check_all_health, check_health

    if args.agent:
        agent = get_agent(args.agent)
        if agent is None:
            known = ", ".join(a.id for a in load_agents())
            print(f"Unknown agent: {args.agent}")
            print(f"Known agents: {known}")
            sys.exit(1)
        reports = [check_health(agent, ping=args.live, timeout=args.timeout)]
    else:
        reports = check_all_health(ping=args.live, timeout=args.timeout)

    for r in reports:
        marker = {"healthy": "+", "installed": "~", "unhealthy": "!", "not installed": "-"}
        m = marker.get(r.status, "?")
        version_str = f"  {r.version}" if r.version else ""
        print(f"  [{m}] {r.agent_id:<12} {r.status:<14}{version_str}")
        if args.verbose and r.ping_result:
            pr = r.ping_result
            print(f"      exit={pr.exit_code}  {pr.duration_s}s  stdout={pr.stdout.strip()[:60]!r}")


def cmd_version(args: argparse.Namespace) -> None:
    """Print version info for one or all agents."""
    from bashful.runner import get_version

    if args.agent:
        agent = get_agent(args.agent)
        if agent is None:
            known = ", ".join(a.id for a in load_agents())
            print(f"Unknown agent: {args.agent}")
            print(f"Known agents: {known}")
            sys.exit(1)
        agents_to_check = [agent]
    else:
        agents_to_check = load_agents()

    for agent in agents_to_check:
        v = get_version(agent)
        if v:
            print(f"  {agent.id:<12} {v}")
        else:
            print(f"  {agent.id:<12} (not available)")


# ---------------------------------------------------------------------------
# Supervisor commands
# ---------------------------------------------------------------------------

def cmd_launch(args: argparse.Namespace) -> None:
    """Launch an agent in the background."""
    from bashful.supervisor import launch

    agent = get_agent(args.agent)
    if agent is None:
        known = ", ".join(a.id for a in load_agents())
        print(f"Unknown agent: {args.agent}", file=sys.stderr)
        print(f"Known agents: {known}", file=sys.stderr)
        sys.exit(1)

    prompt = " ".join(args.prompt)
    if not prompt:
        print("No prompt provided.", file=sys.stderr)
        sys.exit(1)

    # Validate mode
    mode = args.mode
    if not agent.supports_mode(mode):
        supported = ", ".join(agent.modes)
        print(
            f"Error: Agent {agent.id!r} does not support mode {mode!r} "
            f"(supported: {supported})",
            file=sys.stderr,
        )
        sys.exit(1)

    worktree_path = None
    if args.isolate:
        from bashful.worktree import create_worktree
        try:
            wt = create_worktree(f"{agent.id}-{int(time.time())}")
            worktree_path = wt.path
            print(f"  Created worktree: {wt.name} at {wt.path}")
        except (RuntimeError, ValueError) as e:
            print(f"Failed to create worktree: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        job = launch(
            agent,
            prompt,
            cwd=args.cwd,
            worktree=worktree_path,
            mode=mode,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Launched job {job.job_id}")
    print(f"    agent: {job.agent_id}")
    print(f"    mode:  {mode}")
    print(f"    pid:   {job.pid}")
    print(f"    cwd:   {job.cwd}")
    if job.worktree:
        print(f"    worktree: {job.worktree}")
    print(f"\n  Track with: bashful jobs")
    print(f"  Logs:       bashful logs {job.job_id}")


def cmd_jobs(args: argparse.Namespace) -> None:
    """List all jobs and their status."""
    from bashful.supervisor import list_jobs

    state_filter = None
    if args.running:
        state_filter = "running"
    elif args.completed:
        state_filter = "completed"

    jobs = list_jobs(state_filter=state_filter)
    if not jobs:
        print("  No jobs found.")
        return

    for j in jobs:
        if j.duration_s is not None:
            duration = f"{j.duration_s}s"
        elif j.state == "running":
            duration = "running"
        else:
            duration = ""
        exit_str = f"exit={j.exit_code}" if j.exit_code is not None else ""
        wt_str = f"  wt={j.worktree}" if j.worktree else ""
        print(f"  {j.job_id}  {j.agent_id:<10} {j.state:<10} {duration:<10} {exit_str}{wt_str}")


def cmd_logs(args: argparse.Namespace) -> None:
    """Read job logs."""
    from bashful.supervisor import read_logs

    stream = "stderr" if args.stderr else "stdout"
    try:
        content = read_logs(args.job_id, stream=stream, tail=args.tail)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if content.strip():
        print(content)
    else:
        print(f"  (no {stream} output yet)")


def cmd_kill(args: argparse.Namespace) -> None:
    """Kill a running job."""
    from bashful.supervisor import kill_job

    try:
        killed = kill_job(args.job_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if killed:
        print(f"  Killed job {args.job_id}")
    else:
        print(f"  Job {args.job_id} is not running")


def cmd_wait(args: argparse.Namespace) -> None:
    """Block until a job finishes, then print status."""
    from bashful.supervisor import wait_for_job

    try:
        status = wait_for_job(args.job_id, interval=args.interval)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    exit_str = f"exit={status.exit_code}" if status.exit_code is not None else ""
    dur_str = f"{status.duration_s}s" if status.duration_s is not None else ""
    print(f"  {status.job_id}  {status.agent_id}  {status.state}  {dur_str}  {exit_str}")

    if status.state == "failed":
        sys.exit(1)


def cmd_watch(args: argparse.Namespace) -> None:
    """Stream job output until completion."""
    from bashful.supervisor import watch_job

    stream = "stderr" if args.stderr else "stdout"
    try:
        status = watch_job(
            args.job_id,
            interval=args.interval,
            stream=stream,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n--- job {status.job_id} {status.state} ---", file=sys.stderr)

    if status.state == "failed":
        sys.exit(1)


# ---------------------------------------------------------------------------
# Worktree commands
# ---------------------------------------------------------------------------

def cmd_worktree(args: argparse.Namespace) -> None:
    """Dispatch worktree subcommands."""
    wt_dispatch = {
        "create": cmd_wt_create,
        "list": cmd_wt_list,
        "remove": cmd_wt_remove,
    }
    handler = wt_dispatch.get(args.wt_command)
    if handler is None:
        print("Usage: bashful worktree {create|list|remove}")
        sys.exit(1)
    handler(args)


def cmd_wt_create(args: argparse.Namespace) -> None:
    from bashful.worktree import create_worktree

    try:
        wt = create_worktree(args.name, base_ref=args.base)
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Created worktree: {wt.name}")
    print(f"    path:   {wt.path}")
    print(f"    branch: {wt.branch}")
    print(f"    base:   {wt.base_ref}")


def cmd_wt_list(_args: argparse.Namespace) -> None:
    from bashful.worktree import list_worktrees

    wts = list_worktrees()
    if not wts:
        print("  No active worktrees.")
        return

    for wt in wts:
        job_str = f"  job={wt.job_id}" if wt.job_id else ""
        print(f"  {wt.name:<24} {wt.branch:<30} {wt.path}{job_str}")


def cmd_wt_remove(args: argparse.Namespace) -> None:
    from bashful.worktree import remove_worktree

    try:
        removed = remove_worktree(args.name, force=args.force)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if removed:
        print(f"  Removed worktree: {args.name}")
    else:
        print(f"  Worktree not found: {args.name}")


# ---------------------------------------------------------------------------
# Config command
# ---------------------------------------------------------------------------

def cmd_config(_args: argparse.Namespace) -> None:
    """Show current configuration."""
    from bashful.config import show_config
    print(show_config())


# ---------------------------------------------------------------------------
# Review command
# ---------------------------------------------------------------------------

def cmd_review(args: argparse.Namespace) -> None:
    """Run a structured review across agents."""
    from bashful.review import review
    from bashful.fanout import FanoutError

    agent_ids = [a.strip() for a in args.agents.split(",") if a.strip()]
    if not agent_ids:
        print("No agents specified.", file=sys.stderr)
        sys.exit(1)

    prompt = " ".join(args.prompt)
    if not prompt:
        print("No prompt provided.", file=sys.stderr)
        sys.exit(1)

    data = review(
        agent_ids,
        prompt,
        timeout=args.timeout,
        output_format=args.output_format,
        mode=args.mode,
        parallel=args.parallel,
        judge=args.judge,
        judge_timeout=args.judge_timeout,
    )

    any_failed = False
    for i, (agent_id, result) in enumerate(data["results"]):
        if i > 0:
            print()
        if result.ok:
            marker = "OK"
        elif getattr(result, "timed_out", False):
            marker = "TIMEOUT"
            any_failed = True
        else:
            marker = f"FAIL(exit={result.exit_code})"
            any_failed = True
        print(f"--- reviewer: {agent_id} [{marker}] ---")
        if isinstance(result, FanoutError):
            print(result.error)
        elif result.stdout.strip():
            print(result.stdout.strip())

    if data["judge"]:
        j = data["judge"]
        print(f"\n=== synthesis: {j['agent']} ===")
        if j["ok"]:
            print(j.get("stdout", ""))
        else:
            print(f"[synthesis error: {j.get('error', 'unknown')}]")

    if args.save:
        from bashful.artifacts import save_review_artifact
        artifact_id = save_review_artifact(data, mode=args.mode)
        print(f"\n  Saved artifact: {artifact_id}", file=sys.stderr)

    if any_failed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Dialectic command
# ---------------------------------------------------------------------------

def cmd_dialectic(args: argparse.Namespace) -> None:
    """Run a thesis/antithesis/synthesis dialectic."""
    from bashful.dialectic import dialectic
    from bashful.fanout import FanoutError

    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    if len(agents) != 2:
        print("Dialectic requires exactly two agents (e.g. claude,codex).", file=sys.stderr)
        sys.exit(1)

    question = " ".join(args.prompt)
    if not question:
        print("No question provided.", file=sys.stderr)
        sys.exit(1)

    data = dialectic(
        agents[0],
        agents[1],
        question,
        timeout=args.timeout,
        output_format=args.output_format,
        mode=args.mode,
        judge=args.judge,
        judge_timeout=args.judge_timeout,
    )

    any_failed = False

    # Thesis
    t_id, t_result = data["thesis"]
    if t_result.ok:
        t_marker = "OK"
    elif getattr(t_result, "timed_out", False):
        t_marker = "TIMEOUT"
        any_failed = True
    else:
        t_marker = f"FAIL(exit={t_result.exit_code})"
        any_failed = True
    print(f"--- thesis: {t_id} [{t_marker}] ---")
    if isinstance(t_result, FanoutError):
        print(t_result.error)
    elif t_result.stdout.strip():
        print(t_result.stdout.strip())

    # Antithesis
    print()
    a_id, a_result = data["antithesis"]
    if a_result.ok:
        a_marker = "OK"
    elif getattr(a_result, "timed_out", False):
        a_marker = "TIMEOUT"
        any_failed = True
    else:
        a_marker = f"FAIL(exit={a_result.exit_code})"
        any_failed = True
    print(f"--- antithesis: {a_id} [{a_marker}] ---")
    if isinstance(a_result, FanoutError):
        print(a_result.error)
    elif a_result.stdout.strip():
        print(a_result.stdout.strip())

    # Synthesis
    if data["synthesis"]:
        s = data["synthesis"]
        print(f"\n=== synthesis: {s['agent']} ===")
        if s["ok"]:
            print(s.get("stdout", ""))
        else:
            print(f"[synthesis error: {s.get('error', 'unknown')}]")

    if args.save:
        from bashful.artifacts import save_dialectic_artifact
        artifact_id = save_dialectic_artifact(data, mode=args.mode)
        print(f"\n  Saved artifact: {artifact_id}", file=sys.stderr)

    if any_failed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Matrix command
# ---------------------------------------------------------------------------

def cmd_matrix(args: argparse.Namespace) -> None:
    """Run multiple prompts across multiple agents."""
    from bashful.matrix import matrix

    agent_ids = [a.strip() for a in args.agents.split(",") if a.strip()]
    if not agent_ids:
        print("No agents specified.", file=sys.stderr)
        sys.exit(1)

    prompts = args.prompt
    if not prompts:
        print("At least one --prompt required.", file=sys.stderr)
        sys.exit(1)

    rows = matrix(
        agent_ids,
        prompts,
        timeout=args.timeout,
        output_format=args.output_format,
        mode=args.mode,
        parallel=args.parallel,
    )

    from bashful.fanout import FanoutError

    any_failed = False
    for row_idx, row in enumerate(rows):
        if row_idx > 0:
            print()
        print(f"=== prompt: {row['prompt']!r} ===")
        for agent_id, result in row["results"]:
            if result.ok:
                marker = "OK"
            elif result.timed_out:
                marker = "TIMEOUT"
                any_failed = True
            else:
                marker = f"FAIL(exit={result.exit_code})"
                any_failed = True
            print(f"--- {agent_id} [{marker}] ---")
            if isinstance(result, FanoutError):
                print(result.error)
            elif result.stdout.strip():
                print(result.stdout.strip())

    if args.save:
        from bashful.artifacts import save_matrix_artifact
        artifact_id = save_matrix_artifact(rows, agent_ids, mode=args.mode)
        print(f"\n  Saved artifact: {artifact_id}", file=sys.stderr)

    if any_failed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Skill command
# ---------------------------------------------------------------------------

def cmd_skill(args: argparse.Namespace) -> None:
    """Output the bashful skill document."""
    from bashful.skill import generate_skill_doc, get_skill_metadata

    if args.json:
        import json
        print(json.dumps(get_skill_metadata(), indent=2))
    else:
        print(generate_skill_doc(include_state=args.live))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bashful",
        description="Bash-native agent CLI discovery and orchestration.",
    )
    parser.add_argument("--version", action="version", version=f"bashful {__version__}")
    sub = parser.add_subparsers(dest="command")

    # Discovery
    sub.add_parser("list", help="List supported agents and install status")
    sub.add_parser("doctor", help="Print agent readiness summary")

    show_p = sub.add_parser("show", help="Show details for a specific agent")
    show_p.add_argument("agent", help="Agent id (e.g. claude, codex)")

    # Run
    run_p = sub.add_parser("run", help="Run an agent with a prompt (headless)")
    run_p.add_argument("agent", help="Agent id (e.g. claude, gemini)")
    run_p.add_argument("prompt", nargs="+", help="The prompt to send")
    run_p.add_argument("-t", "--timeout", type=float, default=60.0, help="Timeout in seconds")
    run_p.add_argument("-o", "--output-format", help="Output format (text, json, stream-json)")
    run_p.add_argument("-m", "--mode", default=DEFAULT_MODE, choices=VALID_MODES,
                       help=f"Execution mode (default: {DEFAULT_MODE})")
    run_p.add_argument("-v", "--verbose", action="store_true", help="Print run metadata to stderr")
    run_p.add_argument("--save", action="store_true", help="Save result as an artifact")

    # Fanout
    fanout_p = sub.add_parser("fanout", help="Run the same prompt across multiple agents")
    fanout_p.add_argument("agents", help="Comma-separated agent ids (e.g. claude,codex,gemini)")
    fanout_p.add_argument("prompt", nargs="+", help="The prompt to send")
    fanout_p.add_argument("-t", "--timeout", type=float, default=60.0, help="Timeout per agent")
    fanout_p.add_argument("-o", "--output-format", help="Output format")
    fanout_p.add_argument("-m", "--mode", default=DEFAULT_MODE, choices=VALID_MODES,
                          help=f"Execution mode (default: {DEFAULT_MODE})")
    fanout_p.add_argument("--parallel", action="store_true",
                          help="Run agents concurrently (default: sequential)")
    fanout_p.add_argument("--save", action="store_true", help="Save result as an artifact")

    # Compare
    cmp_p = sub.add_parser("compare", help="Compare responses from multiple agents")
    cmp_p.add_argument("agents", help="Comma-separated agent ids (e.g. claude,codex)")
    cmp_p.add_argument("prompt", nargs="+", help="The prompt to send")
    cmp_p.add_argument("-t", "--timeout", type=float, default=60.0, help="Timeout per agent")
    cmp_p.add_argument("-o", "--output-format", help="Output format")
    cmp_p.add_argument("-m", "--mode", default=DEFAULT_MODE, choices=VALID_MODES,
                        help=f"Execution mode (default: {DEFAULT_MODE})")
    cmp_p.add_argument("--parallel", action="store_true", help="Run agents concurrently")
    cmp_p.add_argument("--judge", metavar="AGENT", help="Agent to judge/compare results")
    cmp_p.add_argument("--judge-timeout", type=float, default=120.0,
                        help="Timeout for judge agent (default: 120s)")

    # Artifacts
    art_p = sub.add_parser("artifacts", help="List or show saved artifacts")
    art_p.add_argument("artifact_args", nargs="*", help="[show] <artifact_id>")

    # Health
    ping_p = sub.add_parser("ping", help="Check agent health")
    ping_p.add_argument("agent", nargs="?", help="Agent id (omit for all)")
    ping_p.add_argument("--live", action="store_true", help="Send a test prompt to verify API")
    ping_p.add_argument("-t", "--timeout", type=float, default=30.0, help="Timeout for live ping")
    ping_p.add_argument("-v", "--verbose", action="store_true", help="Show ping details")

    ver_p = sub.add_parser("versions", help="Print version info for agents")
    ver_p.add_argument("agent", nargs="?", help="Agent id (omit for all)")

    # Supervisor
    launch_p = sub.add_parser("launch", help="Launch an agent job in the background")
    launch_p.add_argument("agent", help="Agent id")
    launch_p.add_argument("prompt", nargs="+", help="The prompt to send")
    launch_p.add_argument("--cwd", help="Working directory")
    launch_p.add_argument("--isolate", action="store_true", help="Run in a fresh git worktree")
    launch_p.add_argument("-m", "--mode", default=DEFAULT_MODE, choices=VALID_MODES,
                          help=f"Execution mode (default: {DEFAULT_MODE})")

    jobs_p = sub.add_parser("jobs", help="List background jobs")
    jobs_p.add_argument("--running", action="store_true", help="Show only running jobs")
    jobs_p.add_argument("--completed", action="store_true", help="Show only completed jobs")

    logs_p = sub.add_parser("logs", help="Read job output")
    logs_p.add_argument("job_id", help="Job ID")
    logs_p.add_argument("--stderr", action="store_true", help="Read stderr instead of stdout")
    logs_p.add_argument("--tail", type=int, help="Show last N lines")

    kill_p = sub.add_parser("kill", help="Kill a running job")
    kill_p.add_argument("job_id", help="Job ID")

    wait_p = sub.add_parser("wait", help="Block until a job finishes")
    wait_p.add_argument("job_id", help="Job ID")
    wait_p.add_argument("--interval", type=float, default=1.0,
                         help="Poll interval in seconds (default: 1)")

    watch_p = sub.add_parser("watch", help="Stream job output until completion")
    watch_p.add_argument("job_id", help="Job ID")
    watch_p.add_argument("--stderr", action="store_true", help="Watch stderr instead")
    watch_p.add_argument("--interval", type=float, default=2.0,
                          help="Poll interval in seconds (default: 2)")

    # Worktree
    wt_p = sub.add_parser("worktree", help="Manage git worktrees for isolation")
    wt_sub = wt_p.add_subparsers(dest="wt_command")

    wt_create = wt_sub.add_parser("create", help="Create a new worktree")
    wt_create.add_argument("name", help="Worktree name (e.g. fix-auth)")
    wt_create.add_argument("--base", default="HEAD", help="Base ref (default: HEAD)")

    wt_sub.add_parser("list", help="List active worktrees")

    wt_rm = wt_sub.add_parser("remove", help="Remove a worktree")
    wt_rm.add_argument("name", help="Worktree name")
    wt_rm.add_argument("--force", action="store_true", help="Force removal")

    # Config
    sub.add_parser("config", help="Show current configuration and overrides")

    # Review
    rev_p = sub.add_parser("review", help="Structured review across multiple agents")
    rev_p.add_argument("agents", help="Comma-separated agent ids (e.g. claude,codex)")
    rev_p.add_argument("prompt", nargs="+", help="The target or prompt to review")
    rev_p.add_argument("-t", "--timeout", type=float, default=60.0, help="Timeout per agent")
    rev_p.add_argument("-o", "--output-format", help="Output format")
    rev_p.add_argument("-m", "--mode", default=DEFAULT_MODE, choices=VALID_MODES,
                        help=f"Execution mode (default: {DEFAULT_MODE})")
    rev_p.add_argument("--parallel", action="store_true", help="Run reviewers concurrently")
    rev_p.add_argument("--judge", metavar="AGENT", help="Agent to synthesize reviews")
    rev_p.add_argument("--judge-timeout", type=float, default=120.0,
                        help="Timeout for judge agent (default: 120s)")
    rev_p.add_argument("--save", action="store_true", help="Save result as an artifact")

    # Dialectic
    dia_p = sub.add_parser("dialectic", help="Thesis/antithesis/synthesis dialectic")
    dia_p.add_argument("agents", help="Exactly two comma-separated agent ids (e.g. claude,codex)")
    dia_p.add_argument("prompt", nargs="+", help="The question to explore")
    dia_p.add_argument("-t", "--timeout", type=float, default=60.0, help="Timeout per agent")
    dia_p.add_argument("-o", "--output-format", help="Output format")
    dia_p.add_argument("-m", "--mode", default=DEFAULT_MODE, choices=VALID_MODES,
                        help=f"Execution mode (default: {DEFAULT_MODE})")
    dia_p.add_argument("--judge", metavar="AGENT", help="Agent to synthesize the dialectic")
    dia_p.add_argument("--judge-timeout", type=float, default=120.0,
                        help="Timeout for judge agent (default: 120s)")
    dia_p.add_argument("--save", action="store_true", help="Save result as an artifact")

    # Matrix
    mat_p = sub.add_parser("matrix", help="Run multiple prompts across multiple agents")
    mat_p.add_argument("agents", help="Comma-separated agent ids (e.g. claude,codex)")
    mat_p.add_argument("--prompt", action="append", required=True,
                        help="Prompt to run (repeat for multiple)")
    mat_p.add_argument("-t", "--timeout", type=float, default=60.0, help="Timeout per agent")
    mat_p.add_argument("-o", "--output-format", help="Output format")
    mat_p.add_argument("-m", "--mode", default=DEFAULT_MODE, choices=VALID_MODES,
                        help=f"Execution mode (default: {DEFAULT_MODE})")
    mat_p.add_argument("--parallel", action="store_true", help="Run agents concurrently")
    mat_p.add_argument("--save", action="store_true", help="Save result as an artifact")

    # Skill
    skill_p = sub.add_parser("skill", help="Print the bashful skill document")
    skill_p.add_argument("--live", action="store_true", help="Include live system state")
    skill_p.add_argument("--json", action="store_true", help="Output metadata as JSON")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "list": cmd_list,
        "doctor": cmd_doctor,
        "show": cmd_show,
        "run": cmd_run,
        "fanout": cmd_fanout,
        "compare": cmd_compare,
        "review": cmd_review,
        "dialectic": cmd_dialectic,
        "matrix": cmd_matrix,
        "config": cmd_config,
        "artifacts": cmd_artifacts,
        "ping": cmd_ping,
        "versions": cmd_version,
        "launch": cmd_launch,
        "jobs": cmd_jobs,
        "logs": cmd_logs,
        "kill": cmd_kill,
        "wait": cmd_wait,
        "watch": cmd_watch,
        "worktree": cmd_worktree,
        "skill": cmd_skill,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(0)
    handler(args)


if __name__ == "__main__":
    main()
