"""
tests/test_graph.py
-------------------
Integration tests for Aura's LangGraph StateGraph pipeline.
"""

import pytest
from langchain_core.messages import HumanMessage
from aura.core.graph import aura_graph


@pytest.mark.asyncio
async def test_graph_compilation():
    """Verify graph structure compiles properly."""
    assert aura_graph is not None


@pytest.mark.asyncio
async def test_graph_turn_execution():
    """Test executing a simple graph turn."""
    config = {"configurable": {"thread_id": "test_thread_1", "user_id": "test_user_1"}}
    initial_state = {
        "user_id": "test_user_1",
        "thread_id": "test_thread_1",
        "messages": [HumanMessage(content="Hello Aura!")],
    }

    res = await aura_graph.ainvoke(initial_state, config)
    messages = res.get("messages", [])
    assert len(messages) >= 2
