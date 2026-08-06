"""
aura/memory/cache.py
--------------------
Shared semantic response cache using PostgreSQL pgvector cosine similarity.
"""

import logging
from typing import Any
from aura.config import settings
from aura.db import pool
from aura.memory.store import _get_embedding

logger = logging.getLogger(__name__)

# Personalization keywords that disqualify a query from shared cross-user caching
PERSONALIZATION_KEYWORDS = {"my", "i", "mine", "me", "myself", "our", "us", "preference", "remember"}


def is_personalized(query: str) -> bool:
    """Return True if the query mentions personal pronouns or user-specific facts."""
    words = set(query.lower().split())
    return bool(words.intersection(PERSONALIZATION_KEYWORDS))


async def get_cached_response(query: str) -> str | None:
    """
    Check if a non-personalized query has a high-similarity cached answer in pgvector DB.
    Returns the cached response string if cosine similarity >= CACHE_SIMILARITY_THRESHOLD.
    """
    if is_personalized(query) or not pool:
        return None

    query_emb = _get_embedding(query)
    threshold = settings.CACHE_SIMILARITY_THRESHOLD
    max_distance = 1.0 - threshold  # Cosine distance = 1 - Cosine similarity

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT response, (embedding <=> %s::vector) AS distance
                    FROM semantic_cache
                    WHERE (embedding <=> %s::vector) <= %s
                    ORDER BY distance ASC
                    LIMIT 1;
                    """,
                    (str(query_emb), str(query_emb), max_distance)
                )
                row = await cur.fetchone()
                if row:
                    logger.info("Semantic cache HIT for query '%s' (distance: %.4f)", query, row["distance"])
                    return row["response"]
    except Exception as e:
        logger.warning("Error checking semantic cache: %s", e)

    return None


async def store_cached_response(query: str, response: str) -> None:
    """Cache a general non-personalized Q&A pair in pgvector DB for future reuse."""
    if is_personalized(query) or not query or not response or not pool:
        return

    query_emb = _get_embedding(query)

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO semantic_cache (query, response, embedding)
                    VALUES (%s, %s, %s::vector);
                    """,
                    (query, response, str(query_emb))
                )
                await conn.commit()
                logger.info("Saved query response to shared semantic cache.")
    except Exception as e:
        logger.warning("Failed to save to semantic cache: %s", e)
