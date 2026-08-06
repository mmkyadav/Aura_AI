"""
aura/api/endpoints/memories.py
------------------------------
User long-term memory inspection, manual creation, and deletion endpoints.
"""

from fastapi import APIRouter, HTTPException
from aura.api.schemas import UserMemoryItem, AddMemoryRequest
from aura.memory.store import get_user_facts, add_user_fact, delete_user_fact

router = APIRouter()


@router.get("/users/{user_id}/memories", response_model=list[UserMemoryItem])
async def list_user_memories(user_id: str, q: str | None = None, limit: int = 10):
    """Retrieve long-term facts stored for a user, optionally performing semantic similarity search."""
    facts = await get_user_facts(user_id=user_id, query=q, limit=limit)
    return [
        UserMemoryItem(
            id=str(f.get("id", "")),
            user_id=str(f.get("user_id", user_id)),
            fact=str(f.get("fact", "")),
            category=str(f.get("category", "preference")),
            created_at=str(f.get("created_at", "")),
        )
        for f in facts
    ]


@router.post("/users/{user_id}/memories", response_model=UserMemoryItem)
async def create_user_memory(user_id: str, req: AddMemoryRequest):
    """Manually add a long-term fact or preference for a user."""
    fact_data = await add_user_fact(user_id=user_id, fact=req.fact, category=req.category)
    return UserMemoryItem(
        id=str(fact_data.get("id", "")),
        user_id=user_id,
        fact=str(fact_data.get("fact", req.fact)),
        category=str(fact_data.get("category", req.category)),
        created_at=str(fact_data.get("created_at", "")),
    )


@router.delete("/users/{user_id}/memories/{memory_id}")
async def delete_memory(user_id: str, memory_id: str):
    """Delete a specific user long-term memory fact by ID."""
    success = await delete_user_fact(fact_id=memory_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory item not found or could not be deleted.")
    return {"status": "deleted", "id": memory_id}
