"""Agent Army: 100+ production-grade AI agents on one tiny, model-agnostic core."""
from .agent import Agent, Panel, Pipeline, Result, Tool, agent_tool, parse_action, tool
from .llm import LLM, LLMError, Mock, get_llm

__version__ = "0.2.0"
__all__ = ["Agent", "Panel", "agent_tool", "Pipeline", "Result", "Tool", "tool", "parse_action", "LLM", "LLMError", "Mock", "get_llm"]
