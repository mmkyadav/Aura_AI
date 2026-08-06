"""
aura/core/state.py
------------------
LangGraph execution state schema for Aura.
"""

from typing import Annotated, Any, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AuraState(TypedDict):
    """Execution state passed through Aura's LangGraph pipeline."""
    user_id: str
    thread_id: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Internal routing & memory context fields
    user_memories: list[str]
    cached_response: str | None
    
    # Tool authorization & clarification flags
    awaiting_approval: bool
    pending_tool_calls: list[dict[str, Any]]
    clarification_needed: bool
    clarification_prompt: str | None
