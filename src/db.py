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

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS reference_message_id BIGINT;

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS reference_channel_id BIGINT;

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS reference_author_id BIGINT;

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS reply_mention_enabled BOOLEAN;

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS mentions_users_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS mentions_roles_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE messages
ADD COLUMN IF NOT EXISTS mentions_everyone BOOLEAN NOT NULL DEFAULT FALSE;

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

CREATE TABLE IF NOT EXISTS meal_history (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    meal_name TEXT NOT NULL,
    selected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meal_history_user_time
ON meal_history (guild_id, user_id, selected_at DESC);

CREATE TABLE IF NOT EXISTS meal_options (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    meal_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (guild_id, meal_name)
);

CREATE INDEX IF NOT EXISTS idx_meal_options_guild
ON meal_options (guild_id, created_at ASC);
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
        reference_message_id: int | None = None,
        reference_channel_id: int | None = None,
        reference_author_id: int | None = None,
        reply_mention_enabled: bool | None = None,
        mentions_users_json: str = "[]",
        mentions_roles_json: str = "[]",
        mentions_everyone: bool = False,
    ) -> bool:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        assert self.pool is not None
        query = """
        INSERT INTO messages (
            id, guild_id, channel_id, channel_name, author_id, created_at,
            content, author_display_name, author_avatar_url,
            attachments_json, stickers_json, custom_emojis_json,
            reference_message_id, reference_channel_id, reference_author_id, reply_mention_enabled,
            mentions_users_json, mentions_roles_json, mentions_everyone
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
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
            END,
            reference_message_id = COALESCE(messages.reference_message_id, EXCLUDED.reference_message_id),
            reference_channel_id = COALESCE(messages.reference_channel_id, EXCLUDED.reference_channel_id),
            reference_author_id = COALESCE(messages.reference_author_id, EXCLUDED.reference_author_id),
            reply_mention_enabled = COALESCE(messages.reply_mention_enabled, EXCLUDED.reply_mention_enabled),
            mentions_users_json = CASE
                WHEN messages.mentions_users_json = '[]' AND EXCLUDED.mentions_users_json <> '[]' THEN EXCLUDED.mentions_users_json
                ELSE messages.mentions_users_json
            END,
            mentions_roles_json = CASE
                WHEN messages.mentions_roles_json = '[]' AND EXCLUDED.mentions_roles_json <> '[]' THEN EXCLUDED.mentions_roles_json
                ELSE messages.mentions_roles_json
            END,
            mentions_everyone = messages.mentions_everyone OR EXCLUDED.mentions_everyone
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
                reference_message_id,
                reference_channel_id,
                reference_author_id,
                reply_mention_enabled,
                mentions_users_json,
                mentions_roles_json,
                mentions_everyone,
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
          AND (
            content <> ''
            OR attachments_json <> '[]'
            OR stickers_json <> '[]'
            OR custom_emojis_json <> '[]'
          )
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
          AND created_at >= $3
          AND (
            content <> ''
            OR attachments_json <> '[]'
            OR stickers_json <> '[]'
            OR custom_emojis_json <> '[]'
          );
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
          AND created_at >= $2
          AND (
            content <> ''
            OR attachments_json <> '[]'
            OR stickers_json <> '[]'
            OR custom_emojis_json <> '[]'
          );
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
          AND (
            content <> ''
            OR attachments_json <> '[]'
            OR stickers_json <> '[]'
            OR custom_emojis_json <> '[]'
          )
        GROUP BY guild_id
        ORDER BY cnt DESC;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, author_id, from_time)
            return [(int(r["guild_id"]), int(r["cnt"])) for r in rows]

    async def get_message_type_rows(
        self,
        guild_id: int,
        author_id: int,
        from_time: datetime,
    ) -> List[Tuple[str, str, str]]:
        assert self.pool is not None
        query = """
        SELECT
            content,
            attachments_json,
            stickers_json
        FROM messages
        WHERE guild_id = $1
          AND author_id = $2
          AND created_at >= $3
          AND (
            content <> ''
            OR attachments_json <> '[]'
            OR stickers_json <> '[]'
            OR custom_emojis_json <> '[]'
          );
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id, author_id, from_time)
            return [
                (
                    str(r["content"] or ""),
                    str(r["attachments_json"] or "[]"),
                    str(r["stickers_json"] or "[]"),
                )
                for r in rows
            ]

    async def get_message_type_debug_rows(
        self,
        guild_id: int,
        author_id: int,
        from_time: datetime,
    ) -> List[Tuple[int, int, str, datetime, str, str, str]]:
        assert self.pool is not None
        query = """
        SELECT
            id,
            channel_id,
            channel_name,
            created_at,
            content,
            attachments_json,
            stickers_json
        FROM messages
        WHERE guild_id = $1
          AND author_id = $2
          AND created_at >= $3
        ORDER BY created_at ASC;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id, author_id, from_time)
            return [
                (
                    int(r["id"]),
                    int(r["channel_id"]),
                    str(r["channel_name"] or "unknown-channel"),
                    r["created_at"],
                    str(r["content"] or ""),
                    str(r["attachments_json"] or "[]"),
                    str(r["stickers_json"] or "[]"),
                )
                for r in rows
            ]

    async def get_channel_user_activity_ranking(
        self,
        guild_id: int,
        channel_id: int,
        from_time: datetime,
        limit: int = 10,
    ) -> List[Tuple[int, int]]:
        if limit <= 0:
            return []
        assert self.pool is not None
        query = """
        SELECT
            author_id,
            COUNT(*)::BIGINT AS cnt
        FROM messages
        WHERE guild_id = $1
          AND channel_id = $2
          AND created_at >= $3
          AND (
            content <> ''
            OR attachments_json <> '[]'
            OR stickers_json <> '[]'
            OR custom_emojis_json <> '[]'
          )
        GROUP BY author_id
        ORDER BY cnt DESC, author_id ASC
        LIMIT $4;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id, channel_id, from_time, limit)
            return [(int(r["author_id"]), int(r["cnt"])) for r in rows]

    async def get_channels_top_active_users(
        self,
        guild_id: int,
        from_time: datetime,
    ) -> List[Tuple[int, str, int, int]]:
        assert self.pool is not None
        query = """
        WITH ranked AS (
            SELECT
                channel_id,
                channel_name,
                author_id,
                COUNT(*)::BIGINT AS cnt,
                ROW_NUMBER() OVER (
                    PARTITION BY channel_id
                    ORDER BY COUNT(*) DESC, author_id ASC
                ) AS rn
            FROM messages
            WHERE guild_id = $1
              AND created_at >= $2
              AND (
                content <> ''
                OR attachments_json <> '[]'
                OR stickers_json <> '[]'
                OR custom_emojis_json <> '[]'
              )
            GROUP BY channel_id, channel_name, author_id
        )
        SELECT channel_id, channel_name, author_id, cnt
        FROM ranked
        WHERE rn = 1
        ORDER BY cnt DESC, channel_id ASC;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id, from_time)
            return [
                (
                    int(r["channel_id"]),
                    str(r["channel_name"] or f"channel-{int(r['channel_id'])}"),
                    int(r["author_id"]),
                    int(r["cnt"]),
                )
                for r in rows
            ]

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
            attachments_json, stickers_json, custom_emojis_json,
            reference_message_id, reference_channel_id, reference_author_id, reply_mention_enabled,
            mentions_users_json, mentions_roles_json, mentions_everyone
        FROM messages
        WHERE id = $1;
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, message_id)
            return dict(row) if row is not None else None

    async def get_message_snapshots(self, message_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        if not message_ids:
            return {}
        assert self.pool is not None
        query = """
        SELECT
            id, guild_id, channel_id, channel_name, author_id, created_at,
            content, author_display_name, author_avatar_url,
            attachments_json, stickers_json, custom_emojis_json,
            reference_message_id, reference_channel_id, reference_author_id, reply_mention_enabled,
            mentions_users_json, mentions_roles_json, mentions_everyone
        FROM messages
        WHERE id = ANY($1::BIGINT[]);
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, message_ids)
            return {int(r["id"]): dict(r) for r in rows}

    async def cleanup_empty_snapshot_messages(self, from_time: datetime) -> int:
        assert self.pool is not None
        query = """
        DELETE FROM messages
        WHERE created_at >= $1
          AND content = ''
          AND attachments_json = '[]'
          AND stickers_json = '[]'
          AND custom_emojis_json = '[]';
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, from_time)
            try:
                return int(result.split()[-1])
            except (IndexError, ValueError):
                return 0

    async def get_recent_meal_selections(self, guild_id: int, user_id: int, limit: int) -> List[str]:
        if limit <= 0:
            return []
        assert self.pool is not None
        query = """
        SELECT meal_name
        FROM meal_history
        WHERE guild_id = $1
          AND user_id = $2
        ORDER BY selected_at DESC
        LIMIT $3;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id, user_id, limit)
            return [str(r["meal_name"]) for r in rows]

    async def insert_meal_selection(self, guild_id: int, user_id: int, meal_name: str) -> None:
        assert self.pool is not None
        query = """
        INSERT INTO meal_history (guild_id, user_id, meal_name, selected_at)
        VALUES ($1, $2, $3, NOW());
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, guild_id, user_id, meal_name)

    async def get_meal_history_entries(
        self,
        guild_id: int,
        user_id: int,
        limit: int = 100,
    ) -> List[Tuple[int, str, datetime]]:
        if limit <= 0:
            return []
        assert self.pool is not None
        query = """
        SELECT id, meal_name, selected_at
        FROM meal_history
        WHERE guild_id = $1
          AND user_id = $2
        ORDER BY selected_at DESC, id DESC
        LIMIT $3;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id, user_id, limit)
            return [
                (
                    int(r["id"]),
                    str(r["meal_name"]),
                    r["selected_at"],
                )
                for r in rows
            ]

    async def delete_meal_history_entry(self, guild_id: int, user_id: int, entry_id: int) -> bool:
        assert self.pool is not None
        query = """
        DELETE FROM meal_history
        WHERE guild_id = $1
          AND user_id = $2
          AND id = $3;
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, guild_id, user_id, entry_id)
            try:
                return int(result.split()[-1]) > 0
            except (IndexError, ValueError):
                return False

    async def get_meal_options(self, guild_id: int) -> List[str]:
        assert self.pool is not None
        query = """
        SELECT meal_name
        FROM meal_options
        WHERE guild_id = $1
        ORDER BY created_at ASC, id ASC;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, guild_id)
            return [str(r["meal_name"]) for r in rows]

    async def ensure_meal_options(self, guild_id: int, default_meals: List[str]) -> List[str]:
        existing = await self.get_meal_options(guild_id)
        if existing:
            return existing

        normalized_defaults: List[str] = []
        seen: Set[str] = set()
        for item in default_meals:
            name = str(item).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            normalized_defaults.append(name)

        if not normalized_defaults:
            return []

        assert self.pool is not None
        query = """
        INSERT INTO meal_options (guild_id, meal_name, created_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (guild_id, meal_name) DO NOTHING;
        """
        async with self.pool.acquire() as conn:
            await conn.executemany(query, [(guild_id, name) for name in normalized_defaults])

        return await self.get_meal_options(guild_id)

    async def add_meal_option(self, guild_id: int, meal_name: str) -> bool:
        assert self.pool is not None
        query = """
        INSERT INTO meal_options (guild_id, meal_name, created_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (guild_id, meal_name) DO NOTHING
        RETURNING id;
        """
        async with self.pool.acquire() as conn:
            inserted_id = await conn.fetchval(query, guild_id, meal_name)
            return inserted_id is not None

    async def remove_meal_option(self, guild_id: int, meal_name: str) -> bool:
        assert self.pool is not None
        query = """
        DELETE FROM meal_options
        WHERE guild_id = $1
          AND meal_name = $2;
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, guild_id, meal_name)
            try:
                return int(result.split()[-1]) > 0
            except (IndexError, ValueError):
                return False
