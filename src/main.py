from datetime import datetime, timedelta, timezone
import asyncio
import traceback
from typing import List, Set, Tuple

import discord
from discord import app_commands
from dotenv import load_dotenv

from .config import Settings
from .db import Database


def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}m"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def render_hotmap_text(user_label: str, days: int, rows: List[Tuple[str, int]]) -> str:
    if not rows:
        return f"Here is {user_label} in last {days} day(s) talking hotmap\nNo messages found."

    max_channel_len = max(len(name) for name, _ in rows)
    max_count = max(cnt for _, cnt in rows)
    bar_width = 20

    lines = [f"Here is {user_label} in last {days} day(s) talking hotmap"]
    for channel_name, cnt in rows:
        if max_count == 0:
            bar_len = 1
        else:
            bar_len = max(1, int((cnt / max_count) * bar_width))
        bar = "-" * bar_len
        padded_name = channel_name.ljust(max_channel_len)
        lines.append(f"{padded_name} {bar} {format_count(cnt)}")
    return "\n".join(lines)


class HotmapBot(discord.Client):
    def __init__(self, settings: Settings, db: Database) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        super().__init__(intents=intents)
        self.settings = settings
        self.db = db
        self.tree = app_commands.CommandTree(self)
        self.ingest_log_interval_sec = max(
            5,
            int(getattr(self.settings, "ingest_log_interval_sec", 60)),
        )
        self.total_ingested_messages = 0
        self.window_ingested_messages = 0
        self.metrics_task: asyncio.Task[None] | None = None
        self.startup_thread_scan_done = False
        self.startup_backfill_done = False
        self.history_backfill_on_startup = bool(
            getattr(self.settings, "history_backfill_on_startup", True)
        )
        self.history_backfill_days = max(
            1,
            min(30, int(getattr(self.settings, "history_backfill_days", 30))),
        )

    async def setup_hook(self) -> None:
        print("Starting global slash command sync...")
        synced = await self.tree.sync()
        print(f"Global slash command sync completed. Synced {len(synced)} command(s).")
        if self.metrics_task is None:
            self.metrics_task = asyncio.create_task(self._log_ingest_metrics_loop())
            print(
                "Started ingest metrics logger "
                f"(interval={self.ingest_log_interval_sec}s)."
            )

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} (id={self.user.id if self.user else 'unknown'})")
        if not self.startup_thread_scan_done:
            self.startup_thread_scan_done = True
            asyncio.create_task(self._run_startup_tasks())

    async def on_message(self, message: discord.Message) -> None:
        if not message.guild:
            return
        if message.author.bot:
            return

        channel_name = getattr(message.channel, "name", f"channel-{message.channel.id}")
        inserted = await self.db.insert_message(
            message_id=message.id,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            channel_name=channel_name,
            author_id=message.author.id,
            created_at=message.created_at,
        )
        if inserted:
            self.total_ingested_messages += 1
            self.window_ingested_messages += 1

    async def on_thread_create(self, thread: discord.Thread) -> None:
        await self._try_join_thread(thread, reason="new-thread")

    async def close(self) -> None:
        if self.metrics_task is not None:
            self.metrics_task.cancel()
            try:
                await self.metrics_task
            except asyncio.CancelledError:
                pass
        await super().close()

    async def _log_ingest_metrics_loop(self) -> None:
        interval = self.ingest_log_interval_sec
        while not self.is_closed():
            await asyncio.sleep(interval)
            window_count = self.window_ingested_messages
            self.window_ingested_messages = 0
            rate = window_count / interval
            print(
                "[IngestMetrics] "
                f"window={interval}s, new_messages={window_count}, "
                f"total_messages={self.total_ingested_messages}, rate={rate:.2f}/s"
            )

    async def _run_startup_tasks(self) -> None:
        await self._auto_join_existing_threads()
        if not self.startup_backfill_done and self.history_backfill_on_startup:
            self.startup_backfill_done = True
            await self._run_history_backfill_once()

    async def _auto_join_existing_threads(self) -> None:
        joined = 0
        skipped = 0
        failed = 0
        for guild in self.guilds:
            try:
                threads = await guild.active_threads()
            except Exception as exc:
                print(f"[AutoJoinThreads] Failed to fetch active threads in guild {guild.id}: {exc}")
                failed += 1
                continue

            for thread in threads:
                result = await self._try_join_thread(thread, reason="startup-scan")
                if result == "joined":
                    joined += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    failed += 1

        print(
            "[AutoJoinThreads] Startup scan completed: "
            f"joined={joined}, skipped={skipped}, failed={failed}"
        )

    async def _run_history_backfill_once(self) -> None:
        completed = await self.db.get_kv("history_backfill_completed")
        if completed == "true":
            print("[HistoryBackfill] Already completed before. Skip startup backfill.")
            return

        days = self.history_backfill_days
        anchor_iso = await self.db.get_kv("history_backfill_anchor_utc")
        if anchor_iso:
            anchor_time = datetime.fromisoformat(anchor_iso)
            if anchor_time.tzinfo is None:
                anchor_time = anchor_time.replace(tzinfo=timezone.utc)
        else:
            anchor_time = datetime.now(timezone.utc)
            await self.db.set_kv("history_backfill_anchor_utc", anchor_time.isoformat())

        from_time = anchor_time - timedelta(days=days)
        print(
            "[HistoryBackfill] Starting scan "
            f"for one-time window {from_time.isoformat()} ~ {anchor_time.isoformat()}"
        )

        total_scanned = 0
        total_inserted = 0
        total_failed = 0
        retry_failed_channels = 0

        for guild in self.guilds:
            channels = await self._collect_backfill_targets(guild, from_time)
            channel_ids = [getattr(c, "id", 0) for c in channels]
            done_ids = await self.db.get_done_backfill_channels(channel_ids)
            print(
                "[HistoryBackfill] Guild target summary "
                f"guild={guild.id}, targets={len(channels)}, done={len(done_ids)}"
            )
            for channel in channels:
                channel_id = getattr(channel, "id", 0)
                if channel_id in done_ids:
                    continue
                scanned, inserted, failed, retry_needed = await self._backfill_channel(
                    guild_id=guild.id,
                    channel=channel,
                    from_time=from_time,
                )
                total_scanned += scanned
                total_inserted += inserted
                total_failed += failed
                if not retry_needed:
                    await self.db.mark_backfill_channel_done(channel_id)
                else:
                    retry_failed_channels += 1

        if retry_failed_channels == 0:
            await self.db.set_kv("history_backfill_completed", "true")
            print(
                "[HistoryBackfill] Completed (one-time) "
                f"scanned={total_scanned}, inserted={total_inserted}, failed={total_failed}"
            )
        else:
            print(
                "[HistoryBackfill] Partial run finished; will resume next startup "
                f"retry_failed_channels={retry_failed_channels}, "
                f"scanned={total_scanned}, inserted={total_inserted}, failed={total_failed}"
            )

    async def _collect_backfill_targets(
        self,
        guild: discord.Guild,
        from_time: datetime,
    ) -> List[discord.abc.Messageable]:
        targets: List[discord.abc.Messageable] = []
        seen: Set[int] = set()

        def add_target(target: discord.abc.Messageable, target_id: int) -> None:
            if target_id in seen:
                return
            seen.add(target_id)
            targets.append(target)

        for channel in guild.text_channels:
            add_target(channel, channel.id)

        try:
            active_threads = await guild.active_threads()
            for thread in active_threads:
                add_target(thread, thread.id)
        except Exception as exc:
            print(f"[HistoryBackfill] Failed to fetch active threads in guild {guild.id}: {exc}")

        thread_parents: List[discord.abc.GuildChannel] = list(guild.text_channels)
        for guild_channel in guild.channels:
            if isinstance(guild_channel, discord.ForumChannel):
                thread_parents.append(guild_channel)

        for parent in thread_parents:
            try:
                async for thread in parent.archived_threads(limit=100):
                    archive_ts = thread.archive_timestamp
                    if archive_ts is not None and archive_ts < from_time:
                        break
                    add_target(thread, thread.id)
            except discord.Forbidden:
                continue
            except Exception as exc:
                print(
                    "[HistoryBackfill] Failed to fetch archived threads "
                    f"parent={parent.id} guild={guild.id}: {exc}"
                )

        return targets

    async def _backfill_channel(
        self,
        guild_id: int,
        channel: discord.abc.Messageable,
        from_time: datetime,
    ) -> Tuple[int, int, int, bool]:
        scanned = 0
        inserted = 0
        failed = 0
        retry_needed = False
        channel_id = getattr(channel, "id", 0)
        channel_name = getattr(channel, "name", f"channel-{channel_id}")

        try:
            async for message in channel.history(limit=None, after=from_time, oldest_first=False):
                scanned += 1
                if message.author.bot:
                    continue
                ok = await self.db.insert_message(
                    message_id=message.id,
                    guild_id=guild_id,
                    channel_id=message.channel.id,
                    channel_name=channel_name,
                    author_id=message.author.id,
                    created_at=message.created_at,
                )
                if ok:
                    inserted += 1
                    self.total_ingested_messages += 1
                    self.window_ingested_messages += 1
        except discord.Forbidden:
            failed += 1
        except discord.HTTPException as exc:
            failed += 1
            retry_needed = True
            print(
                "[HistoryBackfill] HTTP error while scanning "
                f"channel={channel_id} guild={guild_id}: {exc}"
            )
        except Exception as exc:
            failed += 1
            retry_needed = True
            print(
                "[HistoryBackfill] Unexpected error while scanning "
                f"channel={channel_id} guild={guild_id}: {exc}"
            )

        print(
            "[HistoryBackfill] Channel scan "
            f"guild={guild_id}, channel={channel_name}({channel_id}), "
            f"scanned={scanned}, inserted={inserted}, failed={failed}"
        )
        return scanned, inserted, failed, retry_needed

    async def _try_join_thread(self, thread: discord.Thread, reason: str) -> str:
        me = thread.guild.me
        if me is not None:
            if thread.members and any(member.id == me.id for member in thread.members):
                return "skipped"

        try:
            await thread.join()
            print(
                "[AutoJoinThreads] Joined thread "
                f"{thread.id} ({thread.name}) in guild {thread.guild.id} via {reason}"
            )
            return "joined"
        except discord.Forbidden:
            print(
                "[AutoJoinThreads] Forbidden joining thread "
                f"{thread.id} ({thread.name}) in guild {thread.guild.id} via {reason}"
            )
            return "failed"
        except discord.HTTPException as exc:
            print(
                "[AutoJoinThreads] HTTP error joining thread "
                f"{thread.id} ({thread.name}) in guild {thread.guild.id} via {reason}: {exc}"
            )
            return "failed"


def build_hotmap_command(bot: HotmapBot) -> app_commands.Command:
    def format_user_label(interaction: discord.Interaction, user: discord.User) -> str:
        guild = interaction.guild
        if guild is not None:
            target_member = guild.get_member(user.id)
            if target_member is not None:
                return f"@{target_member.display_name}"

        name = user.global_name or user.name
        return f"@{name} ({user.id})"

    @app_commands.command(
        name="hotmap",
        description="Show user channel activity hotmap (max 30 days).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(user="Target user", days="Range in days (max 30)")
    async def hotmap(
        interaction: discord.Interaction,
        user: discord.User,
        days: app_commands.Range[int, 1, 30] | None = None,
    ) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need server administrator permission to use this command.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        days_value = days or bot.settings.default_days
        days_value = min(days_value, bot.settings.max_days)
        from_time = datetime.now(timezone.utc) - timedelta(days=days_value)
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.followup.send(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        rows = await bot.db.get_hotmap_counts(
            guild_id=guild_id,
            author_id=user.id,
            from_time=from_time,
        )

        target_label = format_user_label(interaction, user)
        result = render_hotmap_text(target_label, days_value, rows)
        await interaction.followup.send(f"```text\n{result}\n```")

    return hotmap


async def run() -> None:
    load_dotenv()
    settings = Settings.load()
    db = Database(settings.database_url)
    await db.connect()

    bot = HotmapBot(settings, db)
    bot.tree.add_command(build_hotmap_command(bot))

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        print(f"App command error: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)
        message = "Command failed. Please check bot logs."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    try:
        await bot.start(settings.discord_token)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(run())
