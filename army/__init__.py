"""Agent Army: production-grade AI agent templates on one tiny, model-agnostic core."""
from .agent import Agent, Pipeline, Result, Tool, parse_action, tool
from .llm import LLM, LLMError, Mock, get_llm

__version__ = "0.1.0"
__all__ = ["Agent", "Pipeline", "Result", "Tool", "tool", "parse_action", "LLM", "LLMError", "Mock", "get_llm"]
