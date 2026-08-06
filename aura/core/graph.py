"""
aura/core/graph.py
------------------
LangGraph StateGraph definition and compilation for Aura.
"""

import logging
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from aura.core.state import AuraState
from aura.core.nodes import (
    cache_check_node,
    fact_retriever_node,
    router_node,
    tool_execution_node,
    synthesizer_node,
)

logger = logging.getLogger(__name__)


def should_continue(state: AuraState) -> str:
    """Conditional edge routing based on router output."""
    if state.get("cached_response"):
        return END

    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]

    # Check if the LLM requested tool execution
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return END


def build_graph():
    """Assemble and compile Aura's LangGraph StateGraph."""
    builder = StateGraph(AuraState)

    # 1. Add Nodes
    builder.add_node("cache_check", cache_check_node)
    builder.add_node("fact_retriever", fact_retriever_node)
    builder.add_node("router", router_node)
    builder.add_node("tools", tool_execution_node)
    builder.add_node("synthesizer", synthesizer_node)

    # 2. Add Edges
    builder.set_entry_point("cache_check")
    builder.add_edge("cache_check", "fact_retriever")
    builder.add_edge("fact_retriever", "router")

    # 3. Conditional Edge from router
    builder.add_conditional_edges("router", should_continue, {"tools": "tools", END: END})

    # 4. Synthesizer edge
    builder.add_edge("tools", "synthesizer")
    builder.add_edge("synthesizer", END)

    # In-memory checkpointer fallback (can be upgraded to AsyncPostgresSaver when DB runs)
    checkpointer = MemorySaver()
    app = builder.compile(checkpointer=checkpointer)
    logger.info("Aura StateGraph compiled successfully.")
    return app


# Compiled graph instance
aura_graph = build_graph()
