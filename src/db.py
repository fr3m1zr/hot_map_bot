from datetime import datetime, timezone
from typing import List, Set, Tuple

import asyncpg


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_name TEXT NOT NULL,
    author_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_author_time
ON messages (author_id, created_at DESC);

CREATE TABLE IF NOT EXISTS bot_kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS history_backfill_channels (
    channel_id BIGINT PRIMARY KEY,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def insert_message(
        self,
        message_id: int,
        guild_id: int,
        channel_id: int,
        channel_name: str,
        author_id: int,
        created_at: datetime,
    ) -> bool:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        assert self.pool is not None
        query = """
        INSERT INTO messages (id, guild_id, channel_id, channel_name, author_id, created_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (id) DO NOTHING;
        """
        async with self.pool.acquire() as conn:
            status = await conn.execute(
                query,
                message_id,
                guild_id,
                channel_id,
                channel_name,
                author_id,
                created_at,
            )
            return status.endswith("1")

    async def get_hotmap_counts(
        self,
        guild_id: int,
        author_id: int,
        from_time: datetime,
    ) -> List[Tuple[str, int]]:
        assert self.pool is not None
        query = """
        SELECT channel_name, COUNT(*) AS cnt
        FROM messages
        WHERE guild_id = $1
          AND author_id = $2
          AND created_at >= $3
        GROUP BY channel_name
        ORDER BY cnt DESC
        LIMIT 20;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id, author_id, from_time)
            return [(str(r["channel_name"]), int(r["cnt"])) for r in rows]

    async def get_kv(self, key: str) -> str | None:
        assert self.pool is not None
        query = "SELECT value FROM bot_kv WHERE key = $1;"
        async with self.pool.acquire() as conn:
            value = await conn.fetchval(query, key)
            return str(value) if value is not None else None

    async def set_kv(self, key: str, value: str) -> None:
        assert self.pool is not None
        query = """
        INSERT INTO bot_kv (key, value, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (key) DO UPDATE
        SET value = EXCLUDED.value, updated_at = NOW();
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, key, value)

    async def get_done_backfill_channels(self, channel_ids: List[int]) -> Set[int]:
        if not channel_ids:
            return set()
        assert self.pool is not None
        query = """
        SELECT channel_id
        FROM history_backfill_channels
        WHERE channel_id = ANY($1::BIGINT[]);
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, channel_ids)
            return {int(r["channel_id"]) for r in rows}

    async def mark_backfill_channel_done(self, channel_id: int) -> None:
        assert self.pool is not None
        query = """
        INSERT INTO history_backfill_channels (channel_id, completed_at)
        VALUES ($1, NOW())
        ON CONFLICT (channel_id) DO UPDATE
        SET completed_at = NOW();
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, channel_id)
