"""Bashful — bash-native agent CLI discovery and orchestration toolkit."""

__version__ = "0.1.0"

from bashful.agents import load_agents
from bashful.discovery import discover

__all__ = ["load_agents", "discover", "__version__"]
