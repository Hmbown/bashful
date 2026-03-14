"""Tests for health checks."""

from unittest.mock import patch, MagicMock

from bashful.agents import AgentInfo, HeadlessProfile
from bashful.health import check_health, check_all_health, HealthReport
from bashful.runner import RunResult


def _agent(has_headless=True):
    hp = HeadlessProfile(style="flag", args=["-p", "{prompt}"]) if has_headless else None
    return AgentInfo(
        id="test",
        name="Test Agent",
        executable="test-agent",
        description="A test",
        invocation="test-agent -p 'hi'",
        headless=hp,
        version_args=["--version"],
    )


class TestCheckHealth:
    def test_not_installed(self):
        agent = _agent()
        with patch("bashful.health.check_agent") as mock_disc:
            mock_disc.return_value = MagicMock(installed=False, path=None)
            report = check_health(agent)

        assert not report.installed
        assert report.version is None
        assert report.status == "not installed"

    def test_installed_no_ping(self):
        agent = _agent()
        with (
            patch("bashful.health.check_agent") as mock_disc,
            patch("bashful.health.get_version", return_value="2.0.0"),
        ):
            mock_disc.return_value = MagicMock(installed=True, path="/usr/bin/test-agent")
            report = check_health(agent, ping=False)

        assert report.installed
        assert report.version == "2.0.0"
        assert report.ping_ok is None
        assert report.status == "installed"

    def test_healthy_ping(self):
        agent = _agent()
        ping_result = RunResult(
            agent_id="test",
            command=["test-agent", "-p", "ping"],
            stdout="PONG",
            stderr="",
            exit_code=0,
            duration_s=1.5,
        )
        with (
            patch("bashful.health.check_agent") as mock_disc,
            patch("bashful.health.get_version", return_value="2.0.0"),
            patch("bashful.health.run_agent", return_value=ping_result),
        ):
            mock_disc.return_value = MagicMock(installed=True, path="/usr/bin/test-agent")
            report = check_health(agent, ping=True)

        assert report.ping_ok is True
        assert report.status == "healthy"

    def test_unhealthy_ping(self):
        agent = _agent()
        ping_result = RunResult(
            agent_id="test",
            command=["test-agent", "-p", "ping"],
            stdout="",
            stderr="API error",
            exit_code=1,
            duration_s=0.5,
        )
        with (
            patch("bashful.health.check_agent") as mock_disc,
            patch("bashful.health.get_version", return_value="2.0.0"),
            patch("bashful.health.run_agent", return_value=ping_result),
        ):
            mock_disc.return_value = MagicMock(installed=True, path="/usr/bin/test-agent")
            report = check_health(agent, ping=True)

        assert report.ping_ok is False
        assert report.status == "unhealthy"


class TestCheckAllHealth:
    def test_all_missing(self):
        with (
            patch("bashful.health.check_agent") as mock_disc,
            patch("bashful.health.load_agents") as mock_load,
        ):
            mock_load.return_value = [_agent(), _agent()]
            mock_disc.return_value = MagicMock(installed=False, path=None)
            reports = check_all_health(ping=False)

        assert len(reports) == 2
        assert all(r.status == "not installed" for r in reports)
