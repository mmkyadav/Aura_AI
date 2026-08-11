"""
aura/api/schemas.py
-------------------
Pydantic request & response schemas for Aura REST API.
"""

from typing import Any
from pydantic import BaseModel, Field


# User & Thread Schemas
class CreateThreadRequest(BaseModel):
    title: str = Field(default="New Chat", description="Title of the conversation thread")


class ThreadResponse(BaseModel):
    thread_id: str
    user_id: str
    title: str
    created_at: str


# Messaging Schemas
class MessageRequest(BaseModel):
    content: str = Field(..., description="User query or message text")
    stream: bool = Field(default=False, description="Set True for Server-Sent Events (SSE) token streaming")


class ToolCallDetail(BaseModel):
    id: str
    name: str
    args: dict[str, Any]
    via_mcp: bool = Field(default=True, description="Whether tool was executed via Model Context Protocol (MCP)")


class MessageResponse(BaseModel):
    thread_id: str
    user_id: str
    role: str = "assistant"
    content: str
    tool_calls: list[ToolCallDetail] = []
    cached: bool = False


# Tool Approval Schema
class ApproveToolRequest(BaseModel):
    tool_call_id: str
    approved: bool


# Feedback Schema
class FeedbackRequest(BaseModel):
    message_index: int = Field(default=0, description="Index or position of the message being rated")
    rating: str = Field(..., description="Rating: 'thumbs_up' or 'thumbs_down'")
    feedback_text: str = Field(default="", description="Optional comment or feedback text")


class FeedbackResponse(BaseModel):
    status: str
    thread_id: str
    rating: str


# Memory Schemas
class UserMemoryItem(BaseModel):
    id: str
    user_id: str
    fact: str
    category: str
    created_at: str


class AddMemoryRequest(BaseModel):
    fact: str = Field(..., description="User fact or preference to store")
    category: str = Field(default="preference", description="Fact category (e.g. preference, goal, skill)")


# Health Schema
class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
