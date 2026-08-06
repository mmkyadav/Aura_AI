"""
aura/tools/base.py
------------------
Central tool registration and schema export for LangGraph.
"""

from typing import Callable, Any
from langchain_core.tools import tool

# Registry of callable tool functions
TOOL_REGISTRY: dict[str, Callable] = {}
LANGCHAIN_TOOLS: list[Any] = []


def register_tool(name: str):
    """Decorator to register a tool function into the registry."""
    def decorator(fn: Callable):
        TOOL_REGISTRY[name] = fn
        return fn
    return decorator


def get_all_tools() -> list[Any]:
    """Return all registered LangChain tool objects."""
    return LANGCHAIN_TOOLS
