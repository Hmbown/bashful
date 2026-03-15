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
