from datetime import datetime, timedelta, timezone
import asyncio
from io import BytesIO
import re
import traceback
import unicodedata
from typing import List, Set, Tuple

import discord
from discord import app_commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

from .config import Settings
from .db import Database


LOW_ACTIVITY_RATIO_THRESHOLD = 0.005
OTHER_CATEGORY_LABEL = "其他"
MAX_CHART_CHANNELS = 12


def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}m"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def aggregate_hotmap_rows(rows: List[Tuple[str, int]]) -> Tuple[List[Tuple[str, int]], int]:
    total = sum(cnt for _, cnt in rows)
    if total <= 0:
        return [], 0

    grouped_rows: List[Tuple[str, int]] = []
    other_total = 0
    low_active_channel_count = 0

    for channel_name, cnt in rows:
        share = cnt / total
        if share < LOW_ACTIVITY_RATIO_THRESHOLD:
            other_total += cnt
            low_active_channel_count += 1
            continue
        grouped_rows.append((channel_name, cnt))

    if other_total > 0:
        grouped_rows.append((OTHER_CATEGORY_LABEL, other_total))

    return grouped_rows, low_active_channel_count


def clean_channel_label_for_chart(channel_name: str) -> str:
    text = unicodedata.normalize("NFKC", channel_name).replace("\ufffd", "")
    text = re.sub(
        r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF\u200d\ufe0f]",
        "",
        text,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text or "unknown-channel"


def render_hotmap_text(user_label: str, days: int, rows: List[Tuple[str, int]]) -> str:
    if not rows:
        return (
            f"Here is {user_label} in last {days} day(s) talking hotmap\n"
            "No active channels found."
        )

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


def load_chart_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
        if bold
        else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text

    ellipsis = "..."
    available = max(0, max_width - int(draw.textlength(ellipsis, font=font)))
    fitted = ""
    for char in text:
        if draw.textlength(fitted + char, font=font) > available:
            break
        fitted += char
    return fitted.rstrip() + ellipsis


def describe_activity_shape(
    rows: List[Tuple[str, int]],
    low_active_channel_count: int,
) -> Tuple[str, str, float, float]:
    total = sum(cnt for _, cnt in rows)
    if total == 0:
        return "沒有資料", "此區間沒有可用資料", 0, 0

    top_share = rows[0][1] / total
    top_three_share = sum(cnt for _, cnt in rows[:3]) / total
    top_channel = clean_channel_label_for_chart(rows[0][0])

    if top_share >= 0.60 or top_three_share >= 0.85:
        label = "集中型"
        detail = f"集中出沒在 {top_channel}"
    elif top_share <= 0.35 and top_three_share <= 0.65 and len(rows) >= 4:
        label = "分散型"
        detail = "活躍分散在多個頻道"
    else:
        label = "中度集中"
        detail = f"主要出沒在 {top_channel}，也常在其他頻道互動"

    if low_active_channel_count > 0:
        detail = f"{detail}，另有 {low_active_channel_count} 個較低活躍的頻道"

    return label, detail, top_share, top_three_share


def render_hotmap_chart(
    user_label: str,
    days: int,
    all_rows: List[Tuple[str, int]],
    visible_rows: List[Tuple[str, int]],
    low_active_channel_count: int,
) -> BytesIO:
    rows = visible_rows[:MAX_CHART_CHANNELS]
    if (
        len(visible_rows) > MAX_CHART_CHANNELS
        and visible_rows[-1][0] == OTHER_CATEGORY_LABEL
        and rows[-1][0] != OTHER_CATEGORY_LABEL
    ):
        rows = visible_rows[: MAX_CHART_CHANNELS - 1] + [visible_rows[-1]]
    width = 1200
    row_height = 74
    top_padding = 430
    bottom_padding = 52
    height = top_padding + max(1, len(rows)) * row_height + bottom_padding

    background = "#ffffff"
    ink = "#111827"
    muted = "#475467"
    faint = "#98a2b3"
    track = "#edf2f7"
    palette = [
        "#1d4ed8",
        "#059669",
        "#d97706",
        "#dc2626",
        "#7c3aed",
        "#0891b2",
        "#be123c",
        "#4f46e5",
        "#0f766e",
        "#ca8a04",
    ]

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)

    title_font = load_chart_font(40, bold=True)
    subtitle_font = load_chart_font(24)
    verdict_font = load_chart_font(66, bold=True)
    callout_font = load_chart_font(30, bold=True)
    stat_font = load_chart_font(38, bold=True)
    stat_label_font = load_chart_font(19)
    label_font = load_chart_font(25, bold=True)
    value_font = load_chart_font(24, bold=True)

    total_all = sum(cnt for _, cnt in all_rows)
    total_visible = sum(cnt for _, cnt in visible_rows)
    max_count = max((cnt for _, cnt in rows), default=0)
    shape_source = all_rows
    shape_label, shape_detail, top_share, top_three_share = describe_activity_shape(
        shape_source,
        low_active_channel_count,
    )
    top_channel = clean_channel_label_for_chart(shape_source[0][0]) if shape_source else "-"
    verdict_color = "#b42318" if shape_label == "集中型" else "#027a48"
    if shape_label == "中度集中":
        verdict_color = "#b54708"

    title = fit_text(draw, f"{user_label} 的頻道活動分布", title_font, 760)
    draw.text((48, 34), title, fill=ink, font=title_font)
    draw.text(
        (50, 90),
        f"最近 {days} 天",
        fill=muted,
        font=subtitle_font,
    )

    draw.rounded_rectangle((46, 145, 1154, 304), radius=18, fill="#f9fafb", outline="#e4e7ec")
    draw.text((78, 166), shape_label, fill=verdict_color, font=verdict_font)
    callout = (
        f"{top_channel} 佔 {top_share:.0%}"
        if shape_source
        else "這段時間沒有資料"
    )
    draw.text((80, 246), fit_text(draw, callout, callout_font, 470), fill=ink, font=callout_font)

    stat_blocks = [
        (650, "總留言", format_count(total_all)),
        (820, "出沒頻道", str(len(all_rows))),
        (990, "前三占比", f"{top_three_share:.0%}"),
    ]
    for x, label, value in stat_blocks:
        draw.text((x, 176), value, fill=ink, font=stat_font)
        draw.text((x, 228), label, fill=muted, font=stat_label_font)

    detail = shape_detail
    draw.text((52, 328), fit_text(draw, detail, subtitle_font, 1080), fill=muted, font=subtitle_font)

    meter_x = 52
    meter_y = 374
    meter_w = 1096
    meter_h = 28
    draw.rounded_rectangle(
        (meter_x, meter_y, meter_x + meter_w, meter_y + meter_h),
        radius=14,
        fill=track,
    )
    cursor = meter_x
    for idx, (_, cnt) in enumerate(rows):
        segment_w = int(round((cnt / total_visible) * meter_w)) if total_visible else 0
        if idx == len(rows) - 1:
            segment_w = meter_x + meter_w - cursor
        if segment_w <= 0:
            continue
        draw.rounded_rectangle(
            (cursor, meter_y, cursor + segment_w, meter_y + meter_h),
            radius=14,
            fill=palette[idx % len(palette)],
        )
        cursor += segment_w

    if not rows:
        empty_text = "沒有超過門檻的活躍頻道"
        empty_width = draw.textlength(empty_text, font=label_font)
        draw.text(
            ((width - empty_width) / 2, top_padding + 13),
            empty_text,
            fill=muted,
            font=label_font,
        )

    name_x = 96
    bar_x = 370
    bar_w = 560
    value_x = 966
    y = top_padding
    for idx, (channel_name, cnt) in enumerate(rows):
        pct = cnt / total_visible if total_visible else 0
        bar_len = int((cnt / max_count) * bar_w) if max_count else 0
        color = palette[idx % len(palette)]
        channel_label = fit_text(
            draw,
            clean_channel_label_for_chart(channel_name),
            label_font,
            235,
        )

        draw.text((50, y + 20), f"{idx + 1}", fill=faint, font=value_font)
        draw.text((name_x, y + 17), channel_label, fill=ink, font=label_font)
        draw.rounded_rectangle((bar_x, y + 18, bar_x + bar_w, y + 48), radius=15, fill=track)
        draw.rounded_rectangle(
            (bar_x, y + 18, bar_x + max(12, bar_len), y + 48),
            radius=15,
            fill=color,
        )
        draw.text(
            (value_x, y + 15),
            f"{pct:.0%}  ({format_count(cnt)})",
            fill=ink,
            font=value_font,
        )
        if idx < len(rows) - 1:
            draw.line((50, y + row_height - 3, 1150, y + row_height - 3), fill="#eaecf0", width=1)
        y += row_height

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


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
        self.history_backfill_on_startup = bool(self.settings.history_backfill_on_startup)
        self.history_backfill_days = max(1, min(180, int(self.settings.history_backfill_days)))

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
        print(
            "[StartupConfig] "
            f"history_backfill_on_startup={self.history_backfill_on_startup}, "
            f"history_backfill_days={self.history_backfill_days}"
        )
        if not self.startup_backfill_done and self.history_backfill_on_startup:
            self.startup_backfill_done = True
            await self._run_history_backfill_once()
        else:
            print("[HistoryBackfill] Skipped by config or already handled.")

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
        days = self.history_backfill_days
        anchor_time = datetime.now(timezone.utc)
        from_time = anchor_time - timedelta(days=days)
        print(
            "[HistoryBackfill] Starting scan "
            f"for rolling window {from_time.isoformat()} ~ {anchor_time.isoformat()}"
        )

        total_scanned = 0
        total_inserted = 0
        total_failed = 0
        retry_failed_channels = 0

        for guild in self.guilds:
            channels = await self._collect_backfill_targets(guild, from_time)
            print(
                "[HistoryBackfill] Guild target summary "
                f"guild={guild.id}, targets={len(channels)}"
            )
            for channel in channels:
                scanned, inserted, failed, retry_needed = await self._backfill_channel(
                    guild_id=guild.id,
                    channel=channel,
                    from_time=from_time,
                )
                total_scanned += scanned
                total_inserted += inserted
                total_failed += failed
                if retry_needed:
                    retry_failed_channels += 1

        print(
            "[HistoryBackfill] Run finished "
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

        me = guild.me
        skipped_no_access = 0
        for channel in guild.text_channels:
            if me is not None:
                perms = channel.permissions_for(me)
                if not perms.view_channel or not perms.read_message_history:
                    skipped_no_access += 1
                    continue
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

        if skipped_no_access > 0:
            print(
                "[HistoryBackfill] Skipped text channels without access "
                f"guild={guild.id}, count={skipped_no_access}"
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
        earliest_seen: datetime | None = None
        latest_seen: datetime | None = None

        try:
            async for message in channel.history(limit=None, after=from_time, oldest_first=True):
                scanned += 1
                msg_time = message.created_at
                if msg_time.tzinfo is None:
                    msg_time = msg_time.replace(tzinfo=timezone.utc)
                if earliest_seen is None or msg_time < earliest_seen:
                    earliest_seen = msg_time
                if latest_seen is None or msg_time > latest_seen:
                    latest_seen = msg_time
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
            print(
                "[HistoryBackfill] Forbidden while scanning "
                f"channel={channel_id} guild={guild_id} "
                "(need View Channel + Read Message History)."
            )
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
            f"scanned={scanned}, inserted={inserted}, failed={failed}, "
            f"requested_after={from_time.isoformat()}, "
            f"earliest_seen={earliest_seen.isoformat() if earliest_seen else 'none'}, "
            f"latest_seen={latest_seen.isoformat() if latest_seen else 'none'}"
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
        return f"@{name}"

    @app_commands.command(
        name="hotmap",
        description="Show user channel activity hotmap (max 180 days).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(user="Target user", days="Range in days (max 180)")
    async def hotmap(
        interaction: discord.Interaction,
        user: discord.User,
        days: app_commands.Range[int, 1, 180] | None = None,
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
        guild_total_messages = await bot.db.get_hotmap_total_messages(
            guild_id=guild_id,
            author_id=user.id,
            from_time=from_time,
        )
        all_guilds_total_messages = await bot.db.get_hotmap_total_messages_all_guilds(
            author_id=user.id,
            from_time=from_time,
        )
        guild_breakdown = await bot.db.get_hotmap_guild_breakdown(
            author_id=user.id,
            from_time=from_time,
        )

        target_label = format_user_label(interaction, user)
        visible_rows, low_active_channel_count = aggregate_hotmap_rows(rows)
        total_messages = sum(cnt for _, cnt in rows)
        visible_messages = sum(cnt for _, cnt in visible_rows)
        print(
            "[Hotmap] "
            f"guild={guild_id}, author={user.id}, days={days_value}, "
            f"all_channels={len(rows)}, visible_channels={len(visible_rows)}, "
            f"low_active_channels={low_active_channel_count}, "
            f"all_messages={total_messages}, visible_messages={visible_messages}, "
            f"guild_total_messages={guild_total_messages}, "
            f"all_guilds_total_messages={all_guilds_total_messages}, "
            f"guild_breakdown={guild_breakdown}"
        )
        print(f"[HotmapTop10] {rows[:10]}")
        result = render_hotmap_text(target_label, days_value, visible_rows)
        chart = render_hotmap_chart(
            target_label,
            days_value,
            rows,
            visible_rows,
            low_active_channel_count,
        )
        file = discord.File(chart, filename="hotmap.png")
        await interaction.followup.send(f"```text\n{result}\n```", file=file)

    return hotmap


async def run() -> None:
    load_dotenv()
    settings = Settings.load()
    print(
        "[Settings] "
        f"default_days={settings.default_days}, max_days={settings.max_days}, "
        f"history_backfill_on_startup={settings.history_backfill_on_startup}, "
        f"history_backfill_days={settings.history_backfill_days}"
    )
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
