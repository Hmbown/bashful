"""Tests for the Bashful CLI."""

from unittest.mock import patch

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


def test_show_unknown_agent(capsys):
    import pytest
    with pytest.raises(SystemExit):
        main(["show", "nonexistent_agent"])
    out = capsys.readouterr().out
    assert "Unknown agent" in out
