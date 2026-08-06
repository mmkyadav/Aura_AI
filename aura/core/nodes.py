"""
aura/core/nodes.py
------------------
Graph nodes for Aura's LangGraph workflow.
"""

import json
import logging
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage, HumanMessage
from aura.core.state import AuraState
from aura.core.llm_factory import get_resilient_llm
from aura.memory.cache import get_cached_response, store_cached_response
from aura.memory.store import get_user_facts
from aura.tools.base import TOOL_REGISTRY, get_all_tools

logger = logging.getLogger(__name__)

# Base system instructions
SYSTEM_PROMPT_TEMPLATE = """You are Aura, an intelligent, empathetic, and highly context-aware AI assistant.
Your goal is to act as a personal digital companion.

Known facts about the user:
{user_facts_block}

Instructions:
1. Use your own knowledge first when questions can be answered accurately.
2. Refer to previous messages in this conversation history naturally.
3. If an answer requires live or real-time data, use the available tools.
4. If a user request is missing essential information or is highly ambiguous, respond with a clarifying question instead of making unfounded assumptions.
5. Never output raw tool output JSON to the user. Always synthesize information into clean, clear, natural language.
"""


async def cache_check_node(state: AuraState) -> dict:
    """Node 1: Check shared semantic response cache for generic non-personalized queries."""
    messages = state.get("messages", [])
    if not messages:
        return {"cached_response": None}

    last_msg = messages[-1]
    if isinstance(last_msg, HumanMessage):
        query_text = str(last_msg.content).strip()
        cached = await get_cached_response(query_text)
        if cached:
            return {"cached_response": cached}

    return {"cached_response": None}


async def fact_retriever_node(state: AuraState) -> dict:
    """Node 2: Retrieve long-term personalized user facts from pgvector DB."""
    user_id = state.get("user_id", "default_user")
    messages = state.get("messages", [])
    query = str(messages[-1].content) if messages and isinstance(messages[-1], HumanMessage) else None

    facts_data = await get_user_facts(user_id=user_id, query=query, limit=5)
    fact_strings = [f["fact"] for f in facts_data]
    return {"user_memories": fact_strings}


async def router_node(state: AuraState) -> dict:
    """Node 3: Core LLM Router - Evaluates intent, decides tools, or requests clarification."""
    # If semantic cache hit, return cached AI message directly
    if state.get("cached_response"):
        return {"messages": [AIMessage(content=state["cached_response"])]}

    user_facts = state.get("user_memories", [])
    facts_block = "\n".join(f"- {f}" for f in user_facts) if user_facts else "- No specific personal facts stored yet."
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(user_facts_block=facts_block)

    full_messages = [SystemMessage(content=system_prompt)] + list(state["messages"])

    llm = get_resilient_llm(temperature=0.1)
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)

    try:
        response = await llm_with_tools.ainvoke(full_messages)
        return {"messages": [response]}
    except Exception as e:
        logger.error("Router node LLM error: %s", e)
        fallback_msg = AIMessage(content="I encountered a momentary issue processing your request. Please try again.")
        return {"messages": [fallback_msg]}


async def tool_execution_node(state: AuraState) -> dict:
    """Node 4: Execute requested tools and append ToolMessage outputs."""
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None

    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}

    tool_outputs = []
    for tc in last_msg.tool_calls:
        tool_name = tc.get("name")
        tool_args = tc.get("args", {})
        tool_id = tc.get("id")

        tool_fn = TOOL_REGISTRY.get(tool_name)
        if tool_fn:
            try:
                result = tool_fn.invoke(tool_args) if hasattr(tool_fn, "invoke") else tool_fn(**tool_args)
                result_str = str(result)
            except Exception as e:
                logger.error("Tool '%s' execution error: %s", tool_name, e)
                result_str = f"Error executing tool '{tool_name}': {e}"
        else:
            result_str = f"Error: Unknown tool '{tool_name}'."

        tool_outputs.append(ToolMessage(content=result_str, tool_call_id=tool_id, name=tool_name))

    return {"messages": tool_outputs}


async def synthesizer_node(state: AuraState) -> dict:
    """Node 5: Synthesize raw tool outputs into a natural language assistant reply."""
    user_facts = state.get("user_memories", [])
    facts_block = "\n".join(f"- {f}" for f in user_facts) if user_facts else "- None"
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(user_facts_block=facts_block)

    full_messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    llm = get_resilient_llm(temperature=0.1)

    try:
        response = await llm.ainvoke(full_messages)
        
        # Save to semantic cache if initial query was generic
        if len(state["messages"]) >= 2 and isinstance(state["messages"][0], HumanMessage):
            query = str(state["messages"][0].content)
            await store_cached_response(query, str(response.content))

        return {"messages": [response]}
    except Exception as e:
        logger.error("Synthesizer node error: %s", e)
        return {"messages": [AIMessage(content="Here are the results for your request.")]}
