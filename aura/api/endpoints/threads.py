"""
aura/api/endpoints/threads.py
------------------------------
Thread session creation, listing, message retrieval, and messaging (SSE + blocking JSON) endpoints.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from aura.api.schemas import (
    CreateThreadRequest,
    ThreadResponse,
    MessageRequest,
    MessageResponse,
    ToolCallDetail,
    FeedbackRequest,
    FeedbackResponse,
)
from aura.core.graph import aura_graph
from aura.db import pool
from aura.memory.extractor import extract_and_store_user_memories

logger = logging.getLogger(__name__)
router = APIRouter()

# Local sessions folder fallback when PostgreSQL DB is unavailable
SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)


def _get_fallback_file(user_id: str, thread_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{user_id}_{thread_id}.json")


def _save_fallback_message(user_id: str, thread_id: str, role: str, content: str, title: str = "New Chat", tool_calls: list = None):
    file_path = _get_fallback_file(user_id, thread_id)
    data = {"thread_id": thread_id, "user_id": user_id, "title": title, "messages": []}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    msg_obj = {
        "role": role,
        "content": content,
        "created_at": datetime.utcnow().isoformat()
    }
    if tool_calls:
        msg_obj["tool_calls"] = tool_calls

    data["messages"].append(msg_obj)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("Failed writing fallback session file: %s", e)


@router.post("/users/{user_id}/threads", response_model=ThreadResponse)
async def create_thread(user_id: str, req: CreateThreadRequest):
    """Create a new session thread for a specific user."""
    thread_id = str(uuid.uuid4())
    now_str = datetime.utcnow().isoformat()

    if pool:
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO user_threads (thread_id, user_id, title)
                        VALUES (%s, %s, %s);
                        """,
                        (thread_id, user_id, req.title)
                    )
                    await conn.commit()
        except Exception as e:
            logger.warning("DB thread creation fallback: %s", e)

    # Save to local file store fallback as well
    _save_fallback_message(user_id, thread_id, "system", f"Session initialized: {req.title}", title=req.title)

    return ThreadResponse(
        thread_id=thread_id,
        user_id=user_id,
        title=req.title,
        created_at=now_str,
    )


@router.get("/users/{user_id}/threads", response_model=list[ThreadResponse])
async def list_threads(user_id: str):
    """List all active session threads for a user."""
    threads = []
    if pool:
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT thread_id, user_id, title, created_at
                        FROM user_threads
                        WHERE user_id = %s
                        ORDER BY updated_at DESC;
                        """,
                        (user_id,)
                    )
                    rows = await cur.fetchall()
                    if rows:
                        return [
                            ThreadResponse(
                                thread_id=r["thread_id"],
                                user_id=r["user_id"],
                                title=r["title"],
                                created_at=str(r["created_at"]),
                            )
                            for r in rows
                        ]
        except Exception as e:
            logger.warning("DB list threads error: %s", e)

    # Fallback to local sessions directory
    try:
        for fname in os.listdir(SESSIONS_DIR):
            if fname.startswith(f"{user_id}_") and fname.endswith(".json"):
                fpath = os.path.join(SESSIONS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        sdata = json.load(f)
                        threads.append(
                            ThreadResponse(
                                thread_id=sdata.get("thread_id", fname),
                                user_id=user_id,
                                title=sdata.get("title", "Chat Session"),
                                created_at=datetime.utcnow().isoformat(),
                            )
                        )
                except Exception:
                    pass
    except Exception:
        pass

    return threads


@router.get("/users/{user_id}/threads/{thread_id}/messages")
async def get_thread_messages(user_id: str, thread_id: str):
    """Retrieve full message history for a given thread session."""
    if pool:
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT role, content, created_at
                        FROM thread_messages
                        WHERE thread_id = %s
                        ORDER BY created_at ASC;
                        """,
                        (thread_id,)
                    )
                    rows = await cur.fetchall()
                    if rows:
                        return [
                            {"role": r["role"], "content": r["content"], "created_at": str(r["created_at"])}
                            for r in rows
                        ]
        except Exception as e:
            logger.warning("DB get_thread_messages error: %s", e)

    # Local fallback file
    fpath = _get_fallback_file(user_id, thread_id)
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                sdata = json.load(f)
                filtered = [
                    {
                        "role": m.get("role"),
                        "content": m.get("content"),
                        "tool_calls": m.get("tool_calls", []),
                        "created_at": m.get("created_at")
                    }
                    for m in sdata.get("messages", [])
                    if m.get("role") in ("user", "assistant")
                ]
                return filtered
        except Exception:
            pass

    return []


@router.post("/users/{user_id}/threads/{thread_id}/messages")
async def send_message(
    user_id: str,
    thread_id: str,
    req: MessageRequest,
    background_tasks: BackgroundTasks,
):
    """Send a user message to Aura and persist history."""
    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
    initial_state = {
        "user_id": user_id,
        "thread_id": thread_id,
        "messages": [HumanMessage(content=req.content)],
    }

    # Save user message to persistent DB and local file
    if pool:
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO thread_messages (thread_id, user_id, role, content) VALUES (%s, %s, %s, %s);",
                        (thread_id, user_id, "user", req.content)
                    )
                    await conn.commit()
        except Exception:
            pass
    _save_fallback_message(user_id, thread_id, "user", req.content)

    # Handle Server-Sent Events (SSE) streaming mode
    if req.stream:
        async def event_generator():
            try:
                async for event in aura_graph.astream_events(initial_state, config, version="v2"):
                    kind = event.get("event")
                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            yield f"data: {json.dumps({'event': 'token', 'token': chunk.content})}\n\n"
                    elif kind == "on_tool_start":
                        tool_name = event.get("name")
                        yield f"data: {json.dumps({'event': 'tool_start', 'tool': tool_name})}\n\n"

                yield "data: {\"event\": \"done\"}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Standard JSON Blocking Mode
    try:
        final_state = await aura_graph.ainvoke(initial_state, config)
        messages = final_state.get("messages", [])

        assistant_reply = "I'm sorry, I could not generate a response."
        tool_calls_list = []
        is_cached = bool(final_state.get("cached_response"))

        # Find index of the last HumanMessage to scope current turn messages
        last_human_idx = 0
        for idx, msg in enumerate(messages):
            if isinstance(msg, HumanMessage):
                last_human_idx = idx

        current_turn_messages = messages[last_human_idx:]

        # Build mapping of tool execution status from ToolMessages in CURRENT TURN
        mcp_map = {}
        for msg in current_turn_messages:
            if hasattr(msg, "tool_call_id") and getattr(msg, "artifact", None):
                art = getattr(msg, "artifact", {})
                if isinstance(art, dict) and "via_mcp" in art:
                    mcp_map[msg.tool_call_id] = art["via_mcp"]

        # Collect tool calls requested ONLY during the CURRENT TURN
        for msg in current_turn_messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get("id", "")
                    tool_calls_list.append(
                        ToolCallDetail(
                            id=tc_id,
                            name=tc.get("name", ""),
                            args=tc.get("args", {}),
                            via_mcp=mcp_map.get(tc_id, True),
                        )
                    )

        # Extract final assistant reply content from the last non-empty AIMessage in CURRENT TURN
        for msg in reversed(current_turn_messages):
            if isinstance(msg, AIMessage) and msg.content:
                assistant_reply = str(msg.content)
                break

        # Save assistant message to persistent DB and local file
        if pool:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "INSERT INTO thread_messages (thread_id, user_id, role, content) VALUES (%s, %s, %s, %s);",
                            (thread_id, user_id, "assistant", assistant_reply)
                        )
                        await conn.commit()
            except Exception:
                pass

        tool_calls_dicts = [tc.model_dump() for tc in tool_calls_list] if tool_calls_list else []
        _save_fallback_message(user_id, thread_id, "assistant", assistant_reply, tool_calls=tool_calls_dicts)

        # Asynchronously extract long-term user memories in the background
        background_tasks.add_task(
            extract_and_store_user_memories,
            user_id=user_id,
            user_message=req.content,
            assistant_message=assistant_reply,
        )

        return MessageResponse(
            thread_id=thread_id,
            user_id=user_id,
            role="assistant",
            content=assistant_reply,
            tool_calls=tool_calls_list,
            cached=is_cached,
        )
    except Exception as e:
        logger.error("Error in graph turn: %s", e)
        fallback_reply = "I'm processing your request. Could you please clarify your goal?"
        _save_fallback_message(user_id, thread_id, "assistant", fallback_reply)
        return MessageResponse(
            thread_id=thread_id,
            user_id=user_id,
            role="assistant",
            content=fallback_reply,
            tool_calls=[],
            cached=False,
        )


@router.post("/users/{user_id}/threads/{thread_id}/feedback")
async def record_feedback(
    user_id: str,
    thread_id: str,
    req: FeedbackRequest,
):
    """Record user feedback (thumbs up / thumbs down) for a specific assistant response."""
    if pool:
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO message_feedback (thread_id, user_id, message_index, rating, feedback_text)
                        VALUES (%s, %s, %s, %s, %s);
                        """,
                        (thread_id, user_id, req.message_index, req.rating, req.feedback_text)
                    )
                    
                    # If user dislikes response, purge potentially inaccurate cache entry
                    if req.rating == "thumbs_down":
                        await cur.execute("DELETE FROM semantic_cache WHERE created_at < NOW();")
                        
                    await conn.commit()
        except Exception as e:
            logger.warning("Failed to store feedback in DB: %s", e)

    logger.info("Feedback recorded for user %s thread %s: %s (%s)", user_id, thread_id, req.rating, req.feedback_text)
    return FeedbackResponse(status="success", thread_id=thread_id, rating=req.rating)
