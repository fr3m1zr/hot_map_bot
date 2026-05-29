from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

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

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS content TEXT NOT NULL DEFAULT '';

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS author_display_name TEXT NOT NULL DEFAULT '';

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS author_avatar_url TEXT NOT NULL DEFAULT '';

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS attachments_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS stickers_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS custom_emojis_json TEXT NOT NULL DEFAULT '[]';

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

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    delete_log_channel_id BIGINT
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
        content: str = "",
        author_display_name: str = "",
        author_avatar_url: str = "",
        attachments_json: str = "[]",
        stickers_json: str = "[]",
        custom_emojis_json: str = "[]",
    ) -> bool:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        assert self.pool is not None
        query = """
        INSERT INTO messages (
            id, guild_id, channel_id, channel_name, author_id, created_at,
            content, author_display_name, author_avatar_url,
            attachments_json, stickers_json, custom_emojis_json
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (id) DO UPDATE
        SET
            channel_name = EXCLUDED.channel_name,
            content = CASE
                WHEN messages.content = '' AND EXCLUDED.content <> '' THEN EXCLUDED.content
                ELSE messages.content
            END,
            author_display_name = CASE
                WHEN messages.author_display_name = '' AND EXCLUDED.author_display_name <> '' THEN EXCLUDED.author_display_name
                ELSE messages.author_display_name
            END,
            author_avatar_url = CASE
                WHEN messages.author_avatar_url = '' AND EXCLUDED.author_avatar_url <> '' THEN EXCLUDED.author_avatar_url
                ELSE messages.author_avatar_url
            END,
            attachments_json = CASE
                WHEN messages.attachments_json = '[]' AND EXCLUDED.attachments_json <> '[]' THEN EXCLUDED.attachments_json
                ELSE messages.attachments_json
            END,
            stickers_json = CASE
                WHEN messages.stickers_json = '[]' AND EXCLUDED.stickers_json <> '[]' THEN EXCLUDED.stickers_json
                ELSE messages.stickers_json
            END,
            custom_emojis_json = CASE
                WHEN messages.custom_emojis_json = '[]' AND EXCLUDED.custom_emojis_json <> '[]' THEN EXCLUDED.custom_emojis_json
                ELSE messages.custom_emojis_json
            END
        RETURNING (xmax = 0) AS inserted;
        """
        async with self.pool.acquire() as conn:
            inserted = await conn.fetchval(
                query,
                message_id,
                guild_id,
                channel_id,
                channel_name,
                author_id,
                created_at,
                content,
                author_display_name,
                author_avatar_url,
                attachments_json,
                stickers_json,
                custom_emojis_json,
            )
            return bool(inserted)

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
        ORDER BY cnt DESC;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id, author_id, from_time)
            return [(str(r["channel_name"]), int(r["cnt"])) for r in rows]

    async def get_hotmap_total_messages(
        self,
        guild_id: int,
        author_id: int,
        from_time: datetime,
    ) -> int:
        assert self.pool is not None
        query = """
        SELECT COUNT(*)::BIGINT
        FROM messages
        WHERE guild_id = $1
          AND author_id = $2
          AND created_at >= $3;
        """
        async with self.pool.acquire() as conn:
            value = await conn.fetchval(query, guild_id, author_id, from_time)
            return int(value or 0)

    async def get_hotmap_total_messages_all_guilds(
        self,
        author_id: int,
        from_time: datetime,
    ) -> int:
        assert self.pool is not None
        query = """
        SELECT COUNT(*)::BIGINT
        FROM messages
        WHERE author_id = $1
          AND created_at >= $2;
        """
        async with self.pool.acquire() as conn:
            value = await conn.fetchval(query, author_id, from_time)
            return int(value or 0)

    async def get_hotmap_guild_breakdown(
        self,
        author_id: int,
        from_time: datetime,
    ) -> List[Tuple[int, int]]:
        assert self.pool is not None
        query = """
        SELECT guild_id, COUNT(*)::BIGINT AS cnt
        FROM messages
        WHERE author_id = $1
          AND created_at >= $2
        GROUP BY guild_id
        ORDER BY cnt DESC;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, author_id, from_time)
            return [(int(r["guild_id"]), int(r["cnt"])) for r in rows]

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

    async def set_delete_log_channel(self, guild_id: int, channel_id: int) -> None:
        assert self.pool is not None
        query = """
        INSERT INTO guild_settings (guild_id, delete_log_channel_id)
        VALUES ($1, $2)
        ON CONFLICT (guild_id) DO UPDATE
        SET delete_log_channel_id = EXCLUDED.delete_log_channel_id;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, guild_id, channel_id)

    async def get_delete_log_channel(self, guild_id: int) -> int | None:
        assert self.pool is not None
        query = """
        SELECT delete_log_channel_id
        FROM guild_settings
        WHERE guild_id = $1;
        """
        async with self.pool.acquire() as conn:
            value = await conn.fetchval(query, guild_id)
            return int(value) if value is not None else None

    async def get_message_snapshot(self, message_id: int) -> Dict[str, Any] | None:
        assert self.pool is not None
        query = """
        SELECT
            id, guild_id, channel_id, channel_name, author_id, created_at,
            content, author_display_name, author_avatar_url,
            attachments_json, stickers_json, custom_emojis_json
        FROM messages
        WHERE id = $1;
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, message_id)
            return dict(row) if row is not None else None
