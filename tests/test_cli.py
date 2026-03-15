"""Tests for the Bashful CLI."""

from unittest.mock import patch

import pytest

from bashful.cli import main


def test_list_runs(capsys):
    with patch("bashful.discovery.shutil.which", return_value=None):
        main(["list"])
    out = capsys.readouterr().out
    assert "claude" in out
    assert "codex" in out
    assert "not found" in out


def test_list_shows_installed(capsys):
    with patch("bashful.discovery.shutil.which", return_value="/usr/bin/fake"):
        main(["list"])
    out = capsys.readouterr().out
    assert "installed" in out


def test_doctor_runs(capsys):
    with patch("bashful.discovery.shutil.which", return_value=None):
        main(["doctor"])
    out = capsys.readouterr().out
    assert "0/" in out
    assert "Missing" in out


def test_show_known_agent(capsys):
    with patch("bashful.discovery.shutil.which", return_value=None):
        main(["show", "claude"])
    out = capsys.readouterr().out
    assert "Claude Code" in out
    assert "not found" in out
    assert "Modes:" in out
    assert "read" in out


def test_show_unknown_agent(capsys):
    with pytest.raises(SystemExit):
        main(["show", "nonexistent_agent"])
    out = capsys.readouterr().out
    assert "Unknown agent" in out


def test_show_displays_write_mode(capsys):
    with patch("bashful.discovery.shutil.which", return_value=None):
        main(["show", "claude"])
    out = capsys.readouterr().out
    assert "write" in out


def test_run_accepts_mode_flag():
    """Verify --mode is accepted by the run parser."""
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["run", "claude", "hello", "-m", "write"])
    assert args.mode == "write"


def test_run_defaults_to_read_mode():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["run", "claude", "hello"])
    assert args.mode == "read"


def test_fanout_parser():
    """Verify fanout subcommand parses correctly."""
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["fanout", "claude,codex", "hello", "-m", "read", "-t", "30"])
    assert args.agents == "claude,codex"
    assert args.prompt == ["hello"]
    assert args.mode == "read"
    assert args.timeout == 30.0


def test_fanout_exits_nonzero_on_timeout(capsys):
    """Fanout should exit nonzero when any agent times out."""
    from bashful.runner import RunResult

    def timeout_run(agent_ids, prompt, **kwargs):
        return [("claude", RunResult(
            agent_id="claude",
            command=["claude"],
            stdout="",
            stderr="",
            exit_code=-1,
            duration_s=60.0,
            timed_out=True,
            mode="read",
        ))]

    with patch("bashful.fanout.fanout", side_effect=timeout_run):
        with pytest.raises(SystemExit) as exc_info:
            main(["fanout", "claude", "hello"])
        assert exc_info.value.code == 1


def test_launch_accepts_mode_flag():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["launch", "claude", "hello", "-m", "write"])
    assert args.mode == "write"


def test_run_save_flag():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["run", "claude", "hello", "--save"])
    assert args.save is True


def test_run_save_default_off():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["run", "claude", "hello"])
    assert args.save is False


def test_fanout_parallel_flag():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["fanout", "claude,codex", "hello", "--parallel"])
    assert args.parallel is True


def test_fanout_parallel_default_off():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["fanout", "claude,codex", "hello"])
    assert args.parallel is False


def test_fanout_save_flag():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["fanout", "claude,codex", "hello", "--save"])
    assert args.save is True


def test_artifacts_parser_no_id():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["artifacts"])
    assert args.artifact_args == []


def test_artifacts_parser_with_id():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["artifacts", "run-claude-123"])
    assert args.artifact_args == ["run-claude-123"]


def test_artifacts_parser_show_subcommand():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["artifacts", "show", "run-claude-123"])
    assert args.artifact_args == ["show", "run-claude-123"]


def test_compare_parser():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["compare", "claude,codex", "hello", "--judge", "gemini"])
    assert args.agents == "claude,codex"
    assert args.prompt == ["hello"]
    assert args.judge == "gemini"


def test_compare_parser_defaults():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["compare", "claude,codex", "hello"])
    assert args.judge is None
    assert args.parallel is False
    assert args.judge_timeout == 120.0


def test_wait_parser():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["wait", "abc123", "--interval", "0.5"])
    assert args.job_id == "abc123"
    assert args.interval == 0.5


def test_watch_parser():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["watch", "abc123", "--stderr", "--interval", "3.0"])
    assert args.job_id == "abc123"
    assert args.stderr is True
    assert args.interval == 3.0


def test_artifacts_list_empty(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr("bashful.artifacts.ARTIFACTS_DIR", tmp_path / "empty")
    main(["artifacts"])
    out = capsys.readouterr().out
    assert "No saved artifacts" in out


def test_artifacts_show_not_found(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr("bashful.artifacts.ARTIFACTS_DIR", tmp_path / "empty")
    with pytest.raises(SystemExit):
        main(["artifacts", "nonexistent"])
    err = capsys.readouterr().err
    assert "not found" in err


# ---------------------------------------------------------------------------
# Config command
# ---------------------------------------------------------------------------

def test_config_runs(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr("bashful.config.CONFIG_FILE", tmp_path / "nope.json")
    main(["config"])
    out = capsys.readouterr().out
    assert "Config file" in out


# ---------------------------------------------------------------------------
# Review command
# ---------------------------------------------------------------------------

def test_review_parser():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["review", "claude,codex", "Check this.", "--judge", "claude"])
    assert args.agents == "claude,codex"
    assert args.prompt == ["Check this."]
    assert args.judge == "claude"


def test_review_parser_defaults():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["review", "claude,codex", "hello"])
    assert args.judge is None
    assert args.parallel is False
    assert args.judge_timeout == 120.0


# ---------------------------------------------------------------------------
# Dialectic command
# ---------------------------------------------------------------------------

def test_dialectic_parser():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["dialectic", "claude,codex", "Monorepos?", "--judge", "claude"])
    assert args.agents == "claude,codex"
    assert args.prompt == ["Monorepos?"]
    assert args.judge == "claude"


def test_dialectic_parser_defaults():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["dialectic", "claude,codex", "question"])
    assert args.judge is None
    assert args.judge_timeout == 120.0


# ---------------------------------------------------------------------------
# Matrix command
# ---------------------------------------------------------------------------

def test_matrix_parser():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["matrix", "claude,codex", "--prompt", "p1", "--prompt", "p2"])
    assert args.agents == "claude,codex"
    assert args.prompt == ["p1", "p2"]


def test_matrix_parser_defaults():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["matrix", "claude", "--prompt", "p1"])
    assert args.parallel is False
    assert args.save is False
    assert args.timeout == 300.0


def test_review_save_flag():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["review", "claude,codex", "hello", "--save"])
    assert args.save is True


def test_dialectic_save_flag():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["dialectic", "claude,codex", "hello", "--save"])
    assert args.save is True


def test_compare_save_flag():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["compare", "claude,codex", "hello", "--save"])
    assert args.save is True


def test_compare_save_default_off():
    from bashful.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["compare", "claude,codex", "hello"])
    assert args.save is False


# ---------------------------------------------------------------------------
# --json flags
# ---------------------------------------------------------------------------

def test_list_json(capsys):
    with patch("bashful.discovery.shutil.which", return_value=None):
        main(["list", "--json"])
    import json
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert all("id" in r and "installed" in r for r in data)


def test_doctor_json(capsys):
    with patch("bashful.discovery.shutil.which", return_value=None):
        main(["doctor", "--json"])
    import json
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "version" in data
    assert "installed" in data
    assert "missing" in data


def test_jobs_json(capsys):
    with patch("bashful.supervisor.list_jobs", return_value=[]):
        main(["jobs", "--json"])
    import json
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data == []


def test_artifacts_json(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr("bashful.artifacts.ARTIFACTS_DIR", tmp_path / "empty")
    main(["artifacts", "--json"])
    import json
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data == []


def test_dialectic_rejects_wrong_agent_count(capsys):
    from bashful.runner import RunResult

    # The CLI handler should reject != 2 agents
    with pytest.raises(SystemExit) as exc_info:
        main(["dialectic", "claude", "question"])
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "exactly two" in err
