# Discord Hotmap Bot (Python + Docker)

This project provides a scalable Discord bot architecture for large communities.

## Goal

- Command: `/hotmap @user [days]`
- Command: `/set_delete_log #channel`
- Command: `/delete_log_status`
- Output: text-based channel activity hotmap
- Time window: up to 30 days
- Permission: server administrators only
- Optimized for high traffic communities (example: 4,000 members, 20,000+ messages/day)

## Architecture

- `discord.py` bot receives every guild message event (`on_message`)
- Each message is persisted into PostgreSQL
- Slash command aggregates message counts by channel for one target user
- Bot can log deleted messages into a configured channel
- Result is rendered as text bars for quick reading

## Data model

Table: `messages`

- `id`: Discord message id (primary key)
- `guild_id`: guild id
- `channel_id`: channel id
- `channel_name`: channel name snapshot
- `author_id`: message author id
- `created_at`: message time

Index:

- `(author_id, created_at DESC)` for fast user+time range queries

## Quick start

1. Copy env:

   - `cp .env.example .env` (Linux/macOS)
   - On Windows PowerShell: `Copy-Item .env.example .env`

2. Fill values in `.env`:

   - `DISCORD_TOKEN`
   - `DATABASE_URL` (default works with docker compose)

3. Start:

   - `docker compose up --build -d`

4. Wait for global command sync:

   - Global slash commands can take some time to appear in Discord.

5. Check logs:

   - `docker compose logs -f bot`

## Example response

```text
Here is @test_id in last 30 day(s) talking hotmap
general  -------------------- 4.0k
games    ------- 1.0k
learning - 200
image    - 200
```

## Production scaling notes

- Run one bot process first; add sharding when guild/message volume grows.
- Add daily rollup table (materialized counts) if query cost rises.
- Add data retention job (for example keep 90 days raw data).
- Use managed PostgreSQL and monitor index size/IO.
- Add rate-limit handling and retry policy for Discord API calls.

## Important Discord settings

In Discord Developer Portal, enable intents used by this bot:

- `SERVER MEMBERS INTENT`
- `MESSAGE CONTENT INTENT`

## Deleted message log feature

- Use `/set_delete_log #channel` to configure a log channel.
- Use `/delete_log_status` to verify channel config and bot permissions.
- Supports both single delete and bulk delete events.
- When a message is deleted, bot sends an embed containing:
  - Original content
  - User nickname and avatar
  - Delete timestamp
  - Attachment links (image/video/file)
  - Sticker and custom emoji info

### Required permissions for delete log channel

The bot must have these permissions in the configured log channel:

- `View Channel`
- `Send Messages`
- `Embed Links`

Recommended:

- `Read Message History`
- `Attach Files`

### Troubleshooting

- Error: `Failed to send log message: 403 Forbidden (50013) Missing Permissions`
  - Cause: Bot can read delete events but cannot send embed messages to the configured log channel.
  - Fix:
    1. Re-check channel override permissions for bot role/user.
    2. Run `/delete_log_status` and ensure all required permissions pass.
    3. Re-run `/set_delete_log #channel` after permission updates.
