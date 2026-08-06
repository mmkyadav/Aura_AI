"""
aura/api/endpoints/threads.py
------------------------------
Thread session creation, listing, messaging (SSE + blocking JSON), and state management endpoints.
"""

import asyncio
import json
import uuid
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
)
from aura.core.graph import aura_graph
from aura.db import pool
from aura.memory.extractor import extract_and_store_user_memories

router = APIRouter()


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
            pass

    return ThreadResponse(
        thread_id=thread_id,
        user_id=user_id,
        title=req.title,
        created_at=now_str,
    )


@router.get("/users/{user_id}/threads", response_model=list[ThreadResponse])
async def list_threads(user_id: str):
    """List all active session threads for a user."""
    if not pool:
        return []

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
                return [
                    ThreadResponse(
                        thread_id=r["thread_id"],
                        user_id=r["user_id"],
                        title=r["title"],
                        created_at=str(r["created_at"]),
                    )
                    for r in rows
                ]
    except Exception:
        return []


@router.post("/users/{user_id}/threads/{thread_id}/messages")
async def send_message(
    user_id: str,
    thread_id: str,
    req: MessageRequest,
    background_tasks: BackgroundTasks,
):
    """Send a user message to Aura. Supports standard JSON responses or SSE token streaming."""
    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
    initial_state = {
        "user_id": user_id,
        "thread_id": thread_id,
        "messages": [HumanMessage(content=req.content)],
    }

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

        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                assistant_reply = str(msg.content)
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls_list.append(
                            ToolCallDetail(
                                id=tc.get("id", ""),
                                name=tc.get("name", ""),
                                args=tc.get("args", {}),
                            )
                        )
                break

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
        raise HTTPException(status_code=500, detail=f"Error executing Aura graph turn: {e}")
