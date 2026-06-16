from typing import Any, Optional

import asyncpg

from config import settings
from logger import get_logger

logger = get_logger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def create_db_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(settings.asyncpg_url, min_size=2, max_size=10)
    logger.info("Database pool created")


async def close_db_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        logger.info("Database pool closed")


def _get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool


async def execute_query(query: str, *args: Any) -> list[asyncpg.Record]:
    """SELECT multiple rows."""
    async with _get_pool().acquire() as conn:
        return await conn.fetch(query, *args)


async def execute_query_one(query: str, *args: Any) -> Optional[asyncpg.Record]:
    """SELECT a single row."""
    async with _get_pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute_command(query: str, *args: Any) -> str:
    """INSERT / UPDATE / DELETE with no return."""
    async with _get_pool().acquire() as conn:
        return await conn.execute(query, *args)


async def execute_command_with_return(query: str, *args: Any) -> Optional[asyncpg.Record]:
    """INSERT / UPDATE with RETURNING clause."""
    async with _get_pool().acquire() as conn:
        return await conn.fetchrow(query, *args)
