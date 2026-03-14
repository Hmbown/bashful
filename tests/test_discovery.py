"""Tests for agent discovery logic."""

from unittest.mock import patch

from bashful.agents import AgentInfo, load_agents
from bashful.discovery import check_agent, discover


def test_load_agents_returns_list():
    agents = load_agents()
    assert isinstance(agents, list)
    assert len(agents) >= 6
    ids = {a.id for a in agents}
    assert {"claude", "codex", "copilot", "gemini", "qwen", "opencode"} <= ids


def test_check_agent_found():
    agent = AgentInfo(
        id="test", name="Test", executable="test-bin",
        description="test", invocation="test-bin -V",
    )
    with patch("bashful.discovery.shutil.which", return_value="/usr/local/bin/test-bin"):
        result = check_agent(agent)
    assert result.installed is True
    assert result.path == "/usr/local/bin/test-bin"


def test_check_agent_not_found():
    agent = AgentInfo(
        id="fake", name="Fake", executable="no_such_binary_xyz",
        description="fake", invocation="no_such_binary_xyz",
    )
    with patch("bashful.discovery.shutil.which", return_value=None):
        result = check_agent(agent)
    assert result.installed is False
    assert result.path is None


def test_check_agent_with_subcommand_available():
    """Agent with subcommand is installed only when the subcommand works."""
    agent = AgentInfo(
        id="copilot", name="GitHub Copilot CLI", executable="gh",
        description="test", invocation="gh copilot suggest",
        subcommand="copilot",
    )
    with (
        patch("bashful.discovery.shutil.which", return_value="/usr/bin/gh"),
        patch("bashful.discovery._subcommand_available", return_value=True),
    ):
        result = check_agent(agent)
    assert result.installed is True
    assert result.path == "/usr/bin/gh"


def test_check_agent_with_subcommand_missing():
    """gh exists but gh copilot is not installed → not installed."""
    agent = AgentInfo(
        id="copilot", name="GitHub Copilot CLI", executable="gh",
        description="test", invocation="gh copilot suggest",
        subcommand="copilot",
    )
    with (
        patch("bashful.discovery.shutil.which", return_value="/usr/bin/gh"),
        patch("bashful.discovery._subcommand_available", return_value=False),
    ):
        result = check_agent(agent)
    assert result.installed is False
    assert result.path is None


def test_discover_with_mock():
    """Discovery should work even when no real agent CLIs are installed."""
    with patch("bashful.discovery.shutil.which", return_value=None):
        results = discover()
    assert all(not r.installed for r in results)
    assert all(r.path is None for r in results)


def test_discover_with_mock_found():
    with (
        patch("bashful.discovery.shutil.which", return_value="/usr/local/bin/fake"),
        patch("bashful.discovery._subcommand_available", return_value=True),
    ):
        results = discover()
    assert all(r.installed for r in results)
    assert all(r.path == "/usr/local/bin/fake" for r in results)
