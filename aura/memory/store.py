"""
aura/memory/store.py
--------------------
User long-term personalization store using PostgreSQL pgvector.
Vectors are embedded using OpenRouter API / LiteLLM.
"""

import logging
from typing import Any
import litellm

from aura.config import settings
from aura.db import pool

logger = logging.getLogger(__name__)


def _get_embedding(text: str) -> list[float]:
    """Generate a vector embedding for a given text using OpenRouter / LiteLLM."""
    try:
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        if api_key:
            resp = litellm.embedding(
                model="openrouter/openai/text-embedding-3-small",
                input=[text],
                api_key=api_key,
                api_base=settings.OPENROUTER_BASE_URL,
            )
            return resp.data[0]["embedding"]
    except Exception as e:
        logger.warning("Failed to generate embedding via OpenRouter: %s. Using zero fallback vector.", e)
    
    # Fallback 1536-dim dummy vector if embedding API is unavailable
    return [0.0] * 1536


async def add_user_fact(user_id: str, fact: str, category: str = "preference") -> dict[str, Any]:
    """Insert a new user fact with its vector embedding into pgvector DB."""
    if not pool:
        raise RuntimeError("Database pool not initialized.")

    embedding = _get_embedding(fact)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_memories (user_id, fact, category, embedding)
                VALUES (%s, %s, %s, %s::vector)
                RETURNING id, user_id, fact, category, created_at;
                """,
                (user_id, fact, category, str(embedding))
            )
            row = await cur.fetchone()
            await conn.commit()
            logger.info("Saved new long-term fact for user %s: '%s'", user_id, fact)
            return dict(row)


async def get_user_facts(user_id: str, query: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """
    Retrieve top relevant user facts.
    If a query string is provided, performs semantic vector similarity search using pgvector.
    Otherwise, returns the most recent facts.
    """
    if not pool:
        return []

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if query and query.strip():
                query_emb = _get_embedding(query)
                await cur.execute(
                    """
                    SELECT id, user_id, fact, category, created_at, (embedding <=> %s::vector) AS distance
                    FROM user_memories
                    WHERE user_id = %s
                    ORDER BY distance ASC
                    LIMIT %s;
                    """,
                    (str(query_emb), user_id, limit)
                )
            else:
                await cur.execute(
                    """
                    SELECT id, user_id, fact, category, created_at
                    FROM user_memories
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (user_id, limit)
                )

            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_user_fact(fact_id: str, user_id: str) -> bool:
    """Delete a specific user memory fact."""
    if not pool:
        return False

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM user_memories WHERE id = %s AND user_id = %s RETURNING id;",
                (fact_id, user_id)
            )
            deleted = await cur.fetchone()
            await conn.commit()
            return bool(deleted)
