"""Tests for the agent runner."""

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from bashful.agents import AgentInfo, HeadlessProfile
from bashful.runner import run_agent, get_version, RunResult


def _agent(headless=True, version_args=None, modes=None):
    hp = HeadlessProfile(
        style="flag",
        args=["-p", "{prompt}", "-o", "text"],
        output_format_flag="-o",
        output_formats=["text", "json"],
        mode_args={"write": ["--allow-write"]},
    ) if headless else None
    return AgentInfo(
        id="test",
        name="Test Agent",
        executable="test-agent",
        description="A test agent",
        invocation="test-agent -p 'hello'",
        headless=hp,
        version_args=version_args or ["--version"],
        modes=modes or ["read", "write"],
    )


class TestRunAgent:
    def test_successful_run(self):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.stdout = "Hello world"
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", return_value=mock_proc) as mock_run,
        ):
            result = run_agent(agent, "say hello")

        assert result.ok
        assert result.stdout == "Hello world"
        assert result.exit_code == 0
        assert result.mode == "read"
        assert not result.timed_out
        # Check the command was built correctly
        cmd = mock_run.call_args[0][0]
        assert cmd == ["/usr/bin/test-agent", "-p", "say hello", "-o", "text"]

    def test_output_format_override(self):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.stdout = '{"response": "hi"}'
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", return_value=mock_proc) as mock_run,
        ):
            result = run_agent(agent, "say hello", output_format="json")

        cmd = mock_run.call_args[0][0]
        # -o flag should be "json" instead of "text"
        assert "-o" in cmd
        idx = cmd.index("-o")
        assert cmd[idx + 1] == "json"

    def test_nonzero_exit(self):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        mock_proc.stderr = "API quota exceeded"
        mock_proc.returncode = 1

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", return_value=mock_proc),
        ):
            result = run_agent(agent, "say hello")

        assert not result.ok
        assert result.exit_code == 1
        assert "quota" in result.stderr.lower()

    def test_timeout(self):
        agent = _agent()
        exc = subprocess.TimeoutExpired(cmd=["test-agent"], timeout=5)
        exc.stdout = b"partial"
        exc.stderr = b"timed"

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", side_effect=exc),
        ):
            result = run_agent(agent, "say hello", timeout=5)

        assert not result.ok
        assert result.timed_out
        assert result.stdout == "partial"
        assert result.stderr == "timed"

    def test_no_headless_profile_raises(self):
        agent = _agent(headless=False)
        with pytest.raises(ValueError, match="no headless"):
            run_agent(agent, "hello")

    def test_agent_not_installed_raises(self):
        agent = _agent()
        with patch("bashful.runner.shutil.which", return_value=None):
            with pytest.raises(ValueError, match="not found in PATH"):
                run_agent(agent, "hello")

    def test_duration_tracked(self):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.stdout = "ok"
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", return_value=mock_proc),
        ):
            result = run_agent(agent, "test")

        assert result.duration_s >= 0

    def test_write_mode_adds_args(self):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.stdout = "done"
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", return_value=mock_proc) as mock_run,
        ):
            result = run_agent(agent, "fix bug", mode="write")

        assert result.mode == "write"
        cmd = mock_run.call_args[0][0]
        assert "--allow-write" in cmd

    def test_unsupported_mode_raises(self):
        agent = _agent(modes=["read"])
        with pytest.raises(ValueError, match="does not support mode"):
            run_agent(agent, "hello", mode="write")

    def test_invalid_mode_raises(self):
        agent = _agent()
        with pytest.raises(ValueError, match="Invalid mode"):
            run_agent(agent, "hello", mode="execute")

    def test_read_mode_no_extra_args(self):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.stdout = "ok"
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", return_value=mock_proc) as mock_run,
        ):
            result = run_agent(agent, "hello", mode="read")

        cmd = mock_run.call_args[0][0]
        assert "--allow-write" not in cmd


class TestGetVersion:
    def test_returns_version(self):
        agent = _agent(version_args=["--version"])
        mock_proc = MagicMock()
        mock_proc.stdout = "1.2.3\n"
        mock_proc.returncode = 0

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", return_value=mock_proc),
        ):
            v = get_version(agent)

        assert v == "1.2.3"

    def test_not_installed(self):
        agent = _agent()
        with patch("bashful.runner.shutil.which", return_value=None):
            assert get_version(agent) is None

    def test_no_version_args(self):
        agent = _agent(version_args=[])
        with patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"):
            assert get_version(agent) is None

    def test_command_fails(self):
        agent = _agent()
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        mock_proc.returncode = 1

        with (
            patch("bashful.runner.shutil.which", return_value="/usr/bin/test-agent"),
            patch("bashful.runner.subprocess.run", return_value=mock_proc),
        ):
            assert get_version(agent) is None


class TestHeadlessProfileBuildCommand:
    def test_subcommand_style(self):
        hp = HeadlessProfile(style="subcommand", args=["exec", "{prompt}"])
        cmd = hp.build_command("/usr/bin/codex", "fix the bug")
        assert cmd == ["/usr/bin/codex", "exec", "fix the bug"]

    def test_flag_style_with_format(self):
        hp = HeadlessProfile(
            style="flag",
            args=["-p", "{prompt}"],
            output_format_flag="--output-format",
            output_formats=["text", "json"],
        )
        cmd = hp.build_command("/usr/bin/claude", "hello", output_format="json")
        assert cmd == ["/usr/bin/claude", "-p", "hello", "--output-format", "json"]

    def test_unsupported_format_ignored(self):
        hp = HeadlessProfile(
            style="flag",
            args=["-p", "{prompt}"],
            output_format_flag="-o",
            output_formats=["text", "json"],
        )
        cmd = hp.build_command("/usr/bin/agent", "hi", output_format="xml")
        assert "-o" not in cmd or "xml" not in cmd

    def test_mode_args_appended(self):
        hp = HeadlessProfile(
            style="flag",
            args=["-p", "{prompt}"],
            mode_args={"write": ["--dangerously-allow-writes"]},
        )
        cmd = hp.build_command("/usr/bin/agent", "fix it", mode="write")
        assert cmd == ["/usr/bin/agent", "-p", "fix it", "--dangerously-allow-writes"]

    def test_read_mode_no_extra_args(self):
        hp = HeadlessProfile(
            style="flag",
            args=["-p", "{prompt}"],
            mode_args={"write": ["--dangerously-allow-writes"]},
        )
        cmd = hp.build_command("/usr/bin/agent", "read it", mode="read")
        assert cmd == ["/usr/bin/agent", "-p", "read it"]
