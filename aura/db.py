"""
aura/db.py
----------
Database initialization, pool management, and table schema definitions for pgvector.
"""

import logging
from typing import AsyncGenerator
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from aura.config import settings

logger = logging.getLogger(__name__)

# Global async connection pool
pool: AsyncConnectionPool | None = None


async def init_db() -> None:
    """Initialize database tables and pgvector extension."""
    global pool
    logger.info("Initializing PostgreSQL database connection pool...")
    
    # Establish connection pool
    conn_info = settings.sync_database_url
    pool = AsyncConnectionPool(conninfo=conn_info, open=False)
    await pool.open()

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # 1. Enable pgvector extension
            await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await cur.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

            # 2. Table: user_memories (Long-Term Personalization Store)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    fact TEXT NOT NULL,
                    category VARCHAR(100) DEFAULT 'general',
                    embedding vector(1536),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories(user_id);
            """)

            # 3. Table: semantic_cache (Cross-User Shared Knowledge Cache)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    embedding vector(1536),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Table: user_threads (User Session Thread Registry)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS user_threads (
                    thread_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    title VARCHAR(255) DEFAULT 'New Chat',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_user_threads_user_id ON user_threads(user_id);
            """)

            # 5. Table: thread_messages (Permanent Conversation Messages History)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS thread_messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    thread_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_thread_messages_thread_id ON thread_messages(thread_id);
            """)

            await conn.commit()
            logger.info("Database schema and pgvector extension initialized successfully.")


async def close_db() -> None:
    """Close connection pool gracefully."""
    global pool
    if pool:
        await pool.close()
        logger.info("Database connection pool closed.")


async def get_db() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """Dependency / context manager to borrow a connection from the pool."""
    global pool
    if pool is None:
        raise RuntimeError("Database connection pool is not initialized.")
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        yield conn
