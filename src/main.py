from datetime import datetime, timedelta, timezone
import asyncio
import json
import random
from io import BytesIO
import re
import traceback
import unicodedata
from typing import Any, Dict, List, Set, Tuple

import discord # pyright: ignore[reportMissingImports]
from discord import app_commands # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
from PIL import Image, ImageDraw, ImageFont # pyright: ignore[reportMissingImports]

from .config import Settings
from .db import Database


LOW_ACTIVITY_RATIO_THRESHOLD = 0.005
OTHER_CATEGORY_LABEL = "其他"
MAX_CHART_CHANNELS = 12
CUSTOM_EMOJI_REGEX = re.compile(r"<a?:([A-Za-z0-9_]+):(\d+)>")
URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)
UNICODE_EMOJI_REGEX = re.compile(
    r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF\u200d\ufe0f]"
)

MESSAGE_TYPE_ATTACHMENT = "附件"
MESSAGE_TYPE_STICKER = "貼圖"
MESSAGE_TYPE_LINK = "連結"
MESSAGE_TYPE_EMOJI_ONLY = "表符"
MESSAGE_TYPE_TEXT = "文字訊息"
MESSAGE_TYPE_OTHER = "其他"
MESSAGE_TYPE_ORDER = [
    MESSAGE_TYPE_ATTACHMENT,
    MESSAGE_TYPE_STICKER,
    MESSAGE_TYPE_LINK,
    MESSAGE_TYPE_EMOJI_ONLY,
    MESSAGE_TYPE_TEXT,
    MESSAGE_TYPE_OTHER,
]

OTHER_REASON_EMPTY_PENDING = "空內容訊息（待確認存取狀態）"
OTHER_REASON_INACCESSIBLE = "無法存取的訊息（可能已刪除）"
OTHER_REASON_ACCESSIBLE_EMPTY = "可存取但空內容（系統/特殊訊息）"
OTHER_REASON_EMPTY_WITH_STRUCTURED_DATA = "內容為空（但存在結構資料）"
OTHER_REASON_UNRECOGNIZED = "未識別格式"

TABETAI_RECENT_MEAL_COUNT = 4
TABETAI_ANIMATION_STEPS = 8
TABETAI_ANIMATION_DELAY_SEC = 0.20
RANDOM_X_NOT_X_REGEX = re.compile(r"(?P<x>[^\s]{1,20})\s*不\s*(?P=x)")
RANDOM_TRIGGER_PREFIX = "神奇海螺"
RANDOM_USER_COOLDOWN_SEC = 5 * 60
RANDOM_GLOBAL_COOLDOWN_SEC = 20
CHANNEL_TOP_USER_MIN_DIVISOR = 3
CHANNEL_TOP_USER_PAGE_SIZE = 15
YORUSHIKA_TAKE_TRIGGER_TEXT = "拿不拿"
MUSIC_PICK_SONGS: List[Dict[str, str]] = [
    {
        "title": "ただ君に晴れ",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "負け犬にアンコールはいらない",
        "duration": "3:18",
        "spotify_url": "https://open.spotify.com/search/%E3%81%9F%E3%81%A0%E5%90%9B%E3%81%AB%E6%99%B4%E3%82%8C%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "だから僕は音楽を辞めた",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "だから僕は音楽を辞めた",
        "duration": "4:02",
        "spotify_url": "https://open.spotify.com/search/%E3%81%A0%E3%81%8B%E3%82%89%E5%83%95%E3%81%AF%E9%9F%B3%E6%A5%BD%E3%82%92%E8%BE%9E%E3%82%81%E3%81%9F%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "雨とカプチーノ",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "エルマ",
        "duration": "4:29",
        "spotify_url": "https://open.spotify.com/search/%E9%9B%A8%E3%81%A8%E3%82%AB%E3%83%97%E3%83%81%E3%83%BC%E3%83%8E%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "藍二乗",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "だから僕は音楽を辞めた",
        "duration": "4:22",
        "spotify_url": "https://open.spotify.com/search/%E8%97%8D%E4%BA%8C%E4%B9%97%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "花に亡霊",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "盗作",
        "duration": "4:00",
        "spotify_url": "https://open.spotify.com/search/%E8%8A%B1%E3%81%AB%E4%BA%A1%E9%9C%8A%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "春泥棒",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "創作",
        "duration": "4:48",
        "spotify_url": "https://open.spotify.com/search/%E6%98%A5%E6%B3%A5%E6%A3%92%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "思想犯",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "盗作",
        "duration": "4:13",
        "spotify_url": "https://open.spotify.com/search/%E6%80%9D%E6%83%B3%E7%8A%AF%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "左右盲",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "幻燈",
        "duration": "4:36",
        "spotify_url": "https://open.spotify.com/search/%E5%B7%A6%E5%8F%B3%E7%9B%B2%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "夜行",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "創作",
        "duration": "3:22",
        "spotify_url": "https://open.spotify.com/search/%E5%A4%9C%E8%A1%8C%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "晴る",
        "artist": "ヨルシカ",
        "source": "YORUSHIKA",
        "album": "幻燈",
        "duration": "3:45",
        "spotify_url": "https://open.spotify.com/search/%E6%99%B4%E3%82%8B%20%E3%83%A8%E3%83%AB%E3%82%B7%E3%82%AB",
    },
    {
        "title": "ウミユリ海底譚",
        "artist": "n-buna feat. 初音ミク",
        "source": "n-buna VOCALOID",
        "album": "花と水飴、最終電車",
        "duration": "3:59",
        "spotify_url": "https://open.spotify.com/search/%E3%82%A6%E3%83%9F%E3%83%A6%E3%83%AA%E6%B5%B7%E5%BA%95%E8%AD%9A%20n-buna",
    },
    {
        "title": "夜明けと蛍",
        "artist": "n-buna feat. 初音ミク",
        "source": "n-buna VOCALOID",
        "album": "花と水飴、最終電車",
        "duration": "5:09",
        "spotify_url": "https://open.spotify.com/search/%E5%A4%9C%E6%98%8E%E3%81%91%E3%81%A8%E8%9B%8D%20n-buna",
    },
    {
        "title": "メリュー",
        "artist": "n-buna feat. 初音ミク",
        "source": "n-buna VOCALOID",
        "album": "花と水飴、最終電車",
        "duration": "3:34",
        "spotify_url": "https://open.spotify.com/search/%E3%83%A1%E3%83%AA%E3%83%A5%E3%83%BC%20n-buna",
    },
    {
        "title": "背景、夏に溺れる",
        "artist": "n-buna feat. 初音ミク",
        "source": "n-buna VOCALOID",
        "album": "花と水飴、最終電車",
        "duration": "5:15",
        "spotify_url": "https://open.spotify.com/search/%E8%83%8C%E6%99%AF%E3%80%81%E5%A4%8F%E3%81%AB%E6%BA%BA%E3%82%8C%E3%82%8B%20n-buna",
    },
    {
        "title": "透明エレジー",
        "artist": "n-buna feat. GUMI",
        "source": "n-buna VOCALOID",
        "album": "花と水飴、最終電車",
        "duration": "3:43",
        "spotify_url": "https://open.spotify.com/search/%E9%80%8F%E6%98%8E%E3%82%A8%E3%83%AC%E3%82%B8%E3%83%BC%20n-buna",
    },
]
TABETAI_FOODS = [
    "牛肉麵",
    "滷肉飯",
    "咖哩飯",
    "便當",
    "水餃",
    "鍋貼",
    "拉麵",
    "義大利麵",
    "披薩",
    "漢堡",
    "炒飯",
    "炒麵",
    "壽司",
    "韓式拌飯",
    "火鍋",
    "燒肉飯",
    "鹹酥雞",
    "三明治",
    "粥",
    "沙拉",
]


def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}m"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def truncate_text(text: str, limit: int = 1000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def json_item_count(raw: str) -> int:
    text = raw.strip()
    if text in ("", "[]", "null", "None"):
        return 0
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Keep backward-compatible behavior for malformed legacy rows.
        return 1
    if isinstance(parsed, list):
        return len(parsed)
    return 1


def is_emoji_only_content(content: str) -> bool:
    text = content.strip()
    if not text:
        return False
    text = CUSTOM_EMOJI_REGEX.sub("", text)
    text = UNICODE_EMOJI_REGEX.sub("", text)
    return text.strip() == ""


def classify_message_type(content: str, attachments_json: str, stickers_json: str) -> str:
    has_attachment = json_item_count(attachments_json) > 0
    has_sticker = json_item_count(stickers_json) > 0
    has_link = bool(URL_REGEX.search(content))
    emoji_only = is_emoji_only_content(content)

    if has_attachment:
        return MESSAGE_TYPE_ATTACHMENT
    if has_sticker:
        return MESSAGE_TYPE_STICKER
    if has_link:
        return MESSAGE_TYPE_LINK
    if emoji_only:
        return MESSAGE_TYPE_EMOJI_ONLY
    if content.strip():
        return MESSAGE_TYPE_TEXT
    return MESSAGE_TYPE_OTHER


def classify_other_reason(content: str, attachments_json: str, stickers_json: str) -> str:
    text = content.strip()
    attachment_count = json_item_count(attachments_json)
    sticker_count = json_item_count(stickers_json)
    if not text:
        if attachment_count == 0 and sticker_count == 0:
            return OTHER_REASON_EMPTY_PENDING
        return OTHER_REASON_EMPTY_WITH_STRUCTURED_DATA
    return OTHER_REASON_UNRECOGNIZED


def pick_tabetai_choice(
    candidates: List[str],
    recent_meals: List[str],
    excluded_meals: Set[str],
) -> Tuple[str | None, bool]:
    if not candidates:
        return None, False

    recent_set = {item for item in recent_meals if item}
    excluded_set = {item for item in excluded_meals if item}

    strict_pool = [item for item in candidates if item not in recent_set and item not in excluded_set]
    if strict_pool:
        return random.choice(strict_pool), False

    relaxed_pool = [item for item in candidates if item not in excluded_set]
    if relaxed_pool:
        return random.choice(relaxed_pool), True

    cooldown_only_pool = [item for item in candidates if item not in recent_set]
    if cooldown_only_pool:
        return random.choice(cooldown_only_pool), True

    return random.choice(candidates), True


def build_tabetai_animation_embed(
    candidates: List[str],
    step: int,
    total_steps: int,
    redraw: bool = False,
) -> discord.Embed:
    if not candidates:
        candidates = ["---"]

    if len(candidates) >= 3:
        lane_items = random.sample(candidates, 3)
    else:
        lane_items = [random.choice(candidates) for _ in range(3)]
    left, center, right = lane_items

    progress_slots = 10
    filled = max(1, int((step / max(1, total_steps)) * progress_slots))
    progress_bar = ("▰" * filled) + ("▱" * (progress_slots - filled))
    phase_text = "重抽中" if redraw else "抽選中"
    dice_icon = random.choice(["🎲", "🎯", "🍽️"])

    embed = discord.Embed(
        title=f"食べたい {phase_text}...",
        color=discord.Color.blurple(),
    )
    embed.description = (
        f"{dice_icon} 抽到候選：**{center}**\n"
        f"`{left}`  ⇢  **{center}**  ⇢  `{right}`\n"
        f"{progress_bar}  {step}/{total_steps}"
    )
    return embed


def extract_random_x_not_x_options(content: str) -> Tuple[str, str] | None:
    text = content.strip()
    if not text.startswith(RANDOM_TRIGGER_PREFIX):
        return None
    body = text[len(RANDOM_TRIGGER_PREFIX) :].strip()
    if not body:
        return None

    match = RANDOM_X_NOT_X_REGEX.search(body)
    if match is None:
        return None
    x_value = match.group("x").strip()
    if not x_value:
        return None
    return x_value, f"不{x_value}"


def should_trigger_yorushika_pick(content: str) -> bool:
    text = content.strip()
    if not text.startswith(RANDOM_TRIGGER_PREFIX):
        return False
    return YORUSHIKA_TAKE_TRIGGER_TEXT in text


def format_cooldown_duration(until: datetime, now: datetime) -> str:
    remaining_seconds = max(1, int((until - now).total_seconds() + 0.999))
    minutes, seconds = divmod(remaining_seconds, 60)
    if minutes > 0 and seconds > 0:
        return f"{minutes}分{seconds:02d}秒"
    if minutes > 0:
        return f"{minutes}分鐘"
    return f"{seconds}秒"


def build_yorushika_spotify_embed(song: Dict[str, str]) -> discord.Embed:
    embed = discord.Embed(
        title="▶ Spotify Now Playing",
        description=f"**{song['title']}**",
        color=0x1DB954,
    )
    embed.add_field(name="Artist", value=to_text(song.get("artist")), inline=True)
    embed.add_field(name="Source", value=to_text(song.get("source")), inline=True)
    embed.add_field(name="Album", value=to_text(song.get("album")), inline=True)
    embed.add_field(name="Duration", value=to_text(song.get("duration")), inline=True)
    embed.add_field(name="Progress", value="▰▰▰▰▱▱▱▱▱  1:42 / " + to_text(song.get("duration")), inline=False)
    spotify_url = to_text(song.get("spotify_url"))
    if spotify_url:
        embed.add_field(name="Open in Spotify", value=f"[Play on Spotify]({spotify_url})", inline=False)
    embed.set_footer(text="隨機推薦：YORUSHIKA / n-buna VOCALOID")
    return embed


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


def render_message_type_text(
    user_label: str,
    days: int,
    type_counts: Dict[str, int],
    total_messages: int,
    other_reason_counts: Dict[str, int],
) -> str:
    if total_messages <= 0:
        return (
            f"Here is {user_label} in last {days} day(s) message type chart\n"
            "No messages found."
        )

    lines = [f"Here is {user_label} in last {days} day(s) message type chart"]
    for key in MESSAGE_TYPE_ORDER:
        count = type_counts.get(key, 0)
        ratio = (count / total_messages) * 100 if total_messages > 0 else 0
        lines.append(f"{key}: {format_count(count)} ({ratio:.1f}%)")

    other_total = type_counts.get(MESSAGE_TYPE_OTHER, 0)
    if other_total > 0 and other_reason_counts:
        lines.append("")
        lines.append("其他細分:")
        sorted_items = sorted(other_reason_counts.items(), key=lambda x: x[1], reverse=True)
        for reason, count in sorted_items:
            ratio = (count / other_total) * 100 if other_total > 0 else 0
            lines.append(f"- {reason}: {format_count(count)} ({ratio:.1f}%)")

        pending_count = other_reason_counts.get(OTHER_REASON_EMPTY_PENDING, 0)
        if pending_count > 0:
            lines.append("")
            lines.append(
                f"診斷提示: 有 {format_count(pending_count)} 則空內容訊息待確認存取狀態，"
                "可使用 /msgtype_debug 進一步判定是否已刪除、權限不足或系統訊息。"
            )
    return "\n".join(lines)


def render_message_type_debug_text(
    user_label: str,
    days: int,
    total_messages: int,
    type_counts: Dict[str, int],
    other_reason_counts: Dict[str, int],
    problematic_channels: List[Tuple[int, str, int]],
    first_problem_time: datetime | None,
    last_problem_time: datetime | None,
    sample_message_ids: List[int],
    access_check_counts: Dict[str, int],
    access_check_details: List[str],
) -> str:
    lines = [f"Here is {user_label} in last {days} day(s) message snapshot debug"]
    lines.append(f"總訊息數: {format_count(total_messages)}")
    lines.append(f"其他類別數: {format_count(type_counts.get(MESSAGE_TYPE_OTHER, 0))}")

    inaccessible_count = other_reason_counts.get(OTHER_REASON_INACCESSIBLE, 0)
    accessible_empty_count = other_reason_counts.get(OTHER_REASON_ACCESSIBLE_EMPTY, 0)
    pending_count = other_reason_counts.get(OTHER_REASON_EMPTY_PENDING, 0)
    lines.append(f"無法存取訊息: {format_count(inaccessible_count)}")
    if accessible_empty_count > 0:
        lines.append(f"可存取但空內容: {format_count(accessible_empty_count)}")
    if pending_count > 0:
        lines.append(f"待確認存取狀態: {format_count(pending_count)}")

    if not other_reason_counts:
        lines.append("未偵測到其他類別異常。")
        return "\n".join(lines)

    lines.append("")
    lines.append("其他細分:")
    for reason, count in sorted(other_reason_counts.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {reason}: {format_count(count)}")

    if problematic_channels:
        lines.append("")
        lines.append("空內容訊息頻道 Top:")
        for channel_id, channel_name, count in problematic_channels[:8]:
            lines.append(f"- <#{channel_id}> ({channel_name}): {format_count(count)}")

    if first_problem_time is not None and last_problem_time is not None:
        lines.append("")
        lines.append(
            "問題時間範圍: "
            f"{first_problem_time.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"~ {last_problem_time.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

    if sample_message_ids:
        lines.append("")
        sample_text = ", ".join(str(mid) for mid in sample_message_ids[:10])
        lines.append(f"樣本 message_id: {sample_text}")

    if access_check_counts:
        lines.append("")
        lines.append("樣本存取檢查:")
        ordered = ["可存取", "已刪除或不存在", "權限不足", "頻道不可用", "其他錯誤"]
        for key in ordered:
            count = access_check_counts.get(key, 0)
            if count > 0:
                lines.append(f"- {key}: {format_count(count)}")
        for detail in access_check_details[:8]:
            lines.append(f"  - {detail}")

    lines.append("")
    lines.append("建議: 若無法存取訊息偏高，請確認私人討論串加入狀態、頻道讀取權限與回掃涵蓋範圍；若可存取但空內容偏高，通常是系統/特殊訊息。")
    return "\n".join(lines)


def render_message_type_pie_chart(
    user_label: str,
    days: int,
    type_counts: Dict[str, int],
    total_messages: int,
) -> BytesIO:
    width = 1200
    height = 760
    image = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)

    title_font = load_chart_font(40, bold=True)
    subtitle_font = load_chart_font(24)
    label_font = load_chart_font(28, bold=True)
    value_font = load_chart_font(22)
    center_value_font = load_chart_font(46, bold=True)
    center_label_font = load_chart_font(22)

    colors = {
        MESSAGE_TYPE_ATTACHMENT: "#2563eb",
        MESSAGE_TYPE_STICKER: "#7c3aed",
        MESSAGE_TYPE_LINK: "#059669",
        MESSAGE_TYPE_EMOJI_ONLY: "#d97706",
        MESSAGE_TYPE_TEXT: "#0891b2",
        MESSAGE_TYPE_OTHER: "#98a2b3",
    }

    title = fit_text(draw, f"{user_label} 的訊息種類分布", title_font, 980)
    draw.text((46, 34), title, fill="#111827", font=title_font)
    draw.text((48, 92), f"最近 {days} 天", fill="#475467", font=subtitle_font)

    if total_messages <= 0:
        empty_text = "這段時間沒有可分析的訊息"
        tw = draw.textlength(empty_text, font=label_font)
        draw.text(((width - tw) / 2, 350), empty_text, fill="#475467", font=label_font)
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return output

    center_x = 350
    center_y = 420
    radius = 220
    start_angle = -90.0
    for key in MESSAGE_TYPE_ORDER:
        value = type_counts.get(key, 0)
        if value <= 0:
            continue
        sweep = 360.0 * (value / total_messages)
        draw.pieslice(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            start=start_angle,
            end=start_angle + sweep,
            fill=colors[key],
        )
        start_angle += sweep

    inner_radius = 120
    draw.ellipse(
        (
            center_x - inner_radius,
            center_y - inner_radius,
            center_x + inner_radius,
            center_y + inner_radius,
        ),
        fill="#ffffff",
    )
    total_text = format_count(total_messages)
    total_text_width = draw.textlength(total_text, font=center_value_font)
    draw.text(
        (center_x - total_text_width / 2, center_y - 46),
        total_text,
        fill="#111827",
        font=center_value_font,
    )
    center_label = "總訊息"
    center_label_width = draw.textlength(center_label, font=center_label_font)
    draw.text(
        (center_x - center_label_width / 2, center_y + 20),
        center_label,
        fill="#475467",
        font=center_label_font,
    )

    legend_x = 670
    legend_y = 175
    row_height = 82
    for idx, key in enumerate(MESSAGE_TYPE_ORDER):
        y = legend_y + idx * row_height
        value = type_counts.get(key, 0)
        ratio = (value / total_messages) * 100 if total_messages > 0 else 0
        draw.rounded_rectangle((legend_x, y + 14, legend_x + 24, y + 38), radius=6, fill=colors[key])
        draw.text((legend_x + 42, y), key, fill="#111827", font=label_font)
        draw.text(
            (legend_x + 42, y + 42),
            f"{format_count(value)} ({ratio:.1f}%)",
            fill="#475467",
            font=value_font,
        )

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


async def check_message_access_samples(
    bot: "HotmapBot",
    guild: discord.Guild,
    samples: List[Tuple[int, int, str]],
) -> Tuple[Dict[str, int], List[str], Dict[int, str]]:
    counts: Dict[str, int] = {}
    details: List[str] = []
    status_by_message_id: Dict[int, str] = {}

    def add_status(status: str) -> None:
        counts[status] = counts.get(status, 0) + 1

    for message_id, channel_id, channel_name in samples:
        channel_obj: discord.abc.GuildChannel | discord.Thread | None = guild.get_channel(channel_id)
        if channel_obj is None:
            channel_obj = guild.get_thread(channel_id)
        if channel_obj is None:
            try:
                fetched = await bot.fetch_channel(channel_id)
                if isinstance(fetched, (discord.TextChannel, discord.Thread)):
                    channel_obj = fetched
            except discord.Forbidden:
                add_status("權限不足")
                status_by_message_id[message_id] = "權限不足"
                details.append(f"{message_id} / #{channel_name}: 權限不足")
                continue
            except discord.NotFound:
                add_status("頻道不可用")
                status_by_message_id[message_id] = "頻道不可用"
                details.append(f"{message_id} / #{channel_name}: 頻道不存在")
                continue
            except discord.HTTPException:
                add_status("其他錯誤")
                status_by_message_id[message_id] = "其他錯誤"
                details.append(f"{message_id} / #{channel_name}: 頻道查詢失敗")
                continue

        if not isinstance(channel_obj, (discord.TextChannel, discord.Thread)):
            add_status("頻道不可用")
            status_by_message_id[message_id] = "頻道不可用"
            details.append(f"{message_id} / #{channel_name}: 非可讀取文字頻道")
            continue

        try:
            await channel_obj.fetch_message(message_id)
            add_status("可存取")
            status_by_message_id[message_id] = "可存取"
            details.append(f"{message_id} / <#{channel_id}>: 可存取")
        except discord.NotFound:
            add_status("已刪除或不存在")
            status_by_message_id[message_id] = "已刪除或不存在"
            details.append(f"{message_id} / <#{channel_id}>: 已刪除或不存在")
        except discord.Forbidden:
            add_status("權限不足")
            status_by_message_id[message_id] = "權限不足"
            details.append(f"{message_id} / <#{channel_id}>: 權限不足")
        except discord.HTTPException:
            add_status("其他錯誤")
            status_by_message_id[message_id] = "其他錯誤"
            details.append(f"{message_id} / <#{channel_id}>: 讀取失敗")

    return counts, details, status_by_message_id


class HotmapBot(discord.Client):
    def __init__(self, settings: Settings, db: Database) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
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
        self.startup_cleanup_done = False
        self.startup_backfill_done = False
        self.history_backfill_on_startup = bool(self.settings.history_backfill_on_startup)
        self.history_backfill_days = max(1, min(180, int(self.settings.history_backfill_days)))
        self.cleanup_on_startup = bool(self.settings.cleanup_on_startup)
        self.cleanup_days = max(1, min(180, int(self.settings.cleanup_days)))
        self.active_tabetai_sessions: Set[Tuple[int, int]] = set()
        self.random_user_cooldown_until_by_user: Dict[int, datetime] = {}
        self.random_global_cooldown_until: datetime | None = None

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

    def _can_bypass_random_cooldown(self, message: discord.Message) -> bool:
        return (
            isinstance(message.author, discord.Member)
            and message.author.guild_permissions.administrator
        )

    def _get_random_cooldown_messages(self, user_id: int, now: datetime) -> List[str]:
        messages: List[str] = []

        user_until = self.random_user_cooldown_until_by_user.get(user_id)
        if user_until is not None and user_until <= now:
            self.random_user_cooldown_until_by_user.pop(user_id, None)
            user_until = None
        if user_until is not None:
            messages.append(f"使用者 {format_cooldown_duration(user_until, now)}")

        global_until = self.random_global_cooldown_until
        if global_until is not None and global_until <= now:
            self.random_global_cooldown_until = None
            global_until = None
        if global_until is not None:
            messages.append(f"全體 {format_cooldown_duration(global_until, now)}")

        return messages

    async def _send_random_cooldown_notice(
        self,
        message: discord.Message,
        cooldown_messages: List[str],
    ) -> None:
        if not cooldown_messages:
            return
        text = "\n".join(
            [
                "**冷卻中**",
                "-# 目前冷卻規則 5分鐘/使用者 20秒/全體",
            ]
        )
        try:
            await message.reply(
                text,
                mention_author=False,
                delete_after=5,
            )
        except discord.HTTPException as exc:
            print(
                "[RandomCooldown] Failed to reply "
                f"channel={getattr(message.channel, 'id', 'unknown')} "
                f"message_id={message.id}: {exc}"
            )

    def _mark_random_cooldown(self, user_id: int, now: datetime) -> None:
        self.random_user_cooldown_until_by_user[user_id] = now + timedelta(
            seconds=RANDOM_USER_COOLDOWN_SEC
        )
        self.random_global_cooldown_until = now + timedelta(
            seconds=RANDOM_GLOBAL_COOLDOWN_SEC
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.is_system():
            return

        message_text = message.content or ""
        random_triggered = message_text.strip().startswith(RANDOM_TRIGGER_PREFIX)
        random_bypass = self._can_bypass_random_cooldown(message)
        random_replied = False

        if random_triggered and not random_bypass:
            now = datetime.now(timezone.utc)
            cooldown_messages = self._get_random_cooldown_messages(message.author.id, now)
            if cooldown_messages:
                await self._send_random_cooldown_notice(message, cooldown_messages)
                random_triggered = False

        if random_triggered:
            if should_trigger_yorushika_pick(message_text):
                selected_song = random.choice(MUSIC_PICK_SONGS)
                try:
                    await message.reply(
                        embed=build_yorushika_spotify_embed(selected_song),
                        mention_author=False,
                    )
                    random_replied = True
                except discord.HTTPException as exc:
                    print(
                        "[MusicPick] Failed to reply "
                        f"channel={getattr(message.channel, 'id', 'unknown')} "
                        f"message_id={message.id}: {exc}"
                    )
            else:
                random_x_not_x_options = extract_random_x_not_x_options(message_text)
                if random_x_not_x_options is not None:
                    choice = random.choice(list(random_x_not_x_options))
                    try:
                        await message.reply(
                            choice,
                            mention_author=False,
                        )
                        random_replied = True
                    except discord.HTTPException as exc:
                        print(
                            "[RandomXNotX] Failed to reply "
                            f"channel={getattr(message.channel, 'id', 'unknown')} "
                            f"message_id={message.id}: {exc}"
                        )

        if random_replied and not random_bypass:
            self._mark_random_cooldown(message.author.id, datetime.now(timezone.utc))

        if not message.guild:
            return

        snapshot = self._build_message_snapshot(message)
        channel_name = getattr(message.channel, "name", f"channel-{message.channel.id}")
        inserted = await self.db.insert_message(
            message_id=message.id,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            channel_name=channel_name,
            author_id=message.author.id,
            created_at=message.created_at,
            content=snapshot["content"],
            author_display_name=snapshot["author_display_name"],
            author_avatar_url=snapshot["author_avatar_url"],
            attachments_json=json.dumps(snapshot["attachments"], ensure_ascii=False),
            stickers_json=json.dumps(snapshot["stickers"], ensure_ascii=False),
            custom_emojis_json=json.dumps(snapshot["custom_emojis"], ensure_ascii=False),
            reference_message_id=snapshot["reference_message_id"],
            reference_channel_id=snapshot["reference_channel_id"],
            reference_author_id=snapshot["reference_author_id"],
            reply_mention_enabled=snapshot["reply_mention_enabled"],
            mentions_users_json=json.dumps(snapshot["mentions_users"], ensure_ascii=False),
            mentions_roles_json=json.dumps(snapshot["mentions_roles"], ensure_ascii=False),
            mentions_everyone=bool(snapshot["mentions_everyone"]),
        )
        if inserted:
            self.total_ingested_messages += 1
            self.window_ingested_messages += 1

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        if payload.guild_id is None:
            return

        delete_log_channel_id = await self.db.get_delete_log_channel(payload.guild_id)
        if delete_log_channel_id is None:
            print(
                "[DeleteLog] Raw delete received but no log channel configured "
                f"guild={payload.guild_id}, channel={payload.channel_id}, message_id={payload.message_id}"
            )
            return

        print(
            "[DeleteLog] Raw delete received "
            f"guild={payload.guild_id}, channel={payload.channel_id}, "
            f"message_id={payload.message_id}, cached={payload.cached_message is not None}"
        )

        snapshot: Dict[str, Any] | None = None
        no_snapshot_reason: str | None = None
        cached_attachments: List[discord.Attachment] | None = None
        if payload.cached_message is not None:
            if payload.cached_message.author.bot:
                print(
                    "[DeleteLog] Skip bot message delete log "
                    f"guild={payload.guild_id}, channel={payload.channel_id}, message_id={payload.message_id}"
                )
                return
            if payload.cached_message.is_system():
                print(
                    "[DeleteLog] Skip system message delete log "
                    f"guild={payload.guild_id}, channel={payload.channel_id}, message_id={payload.message_id}"
                )
                return
            snapshot = self._build_message_snapshot(payload.cached_message)
            snapshot["message_id"] = payload.cached_message.id
            snapshot["guild_id"] = payload.cached_message.guild.id if payload.cached_message.guild else payload.guild_id
            snapshot["channel_id"] = payload.cached_message.channel.id
            snapshot["channel_name"] = getattr(payload.cached_message.channel, "name", f"channel-{payload.cached_message.channel.id}")
            snapshot["author_id"] = payload.cached_message.author.id
            snapshot["created_at"] = payload.cached_message.created_at
            cached_attachments = list(payload.cached_message.attachments)
        else:
            db_row = await self.db.get_message_snapshot(payload.message_id)
            if db_row is not None:
                snapshot = self._build_snapshot_from_db_row(db_row)
            else:
                no_snapshot_reason = (
                    "未找到訊息快照；可能原因：訊息建立時 bot 不在線、缺少頻道/討論串權限、"
                    "快取已過期，或訊息建立後很快被刪除。"
                )

        await self._send_deleted_message_log(
            guild_id=payload.guild_id,
            delete_log_channel_id=delete_log_channel_id,
            message_id=payload.message_id,
            fallback_channel_id=payload.channel_id,
            snapshot=snapshot,
            cached_attachments=cached_attachments,
            no_snapshot_reason=no_snapshot_reason,
        )

    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent) -> None:
        if payload.guild_id is None:
            return

        delete_log_channel_id = await self.db.get_delete_log_channel(payload.guild_id)
        if delete_log_channel_id is None:
            print(
                "[DeleteLog] Raw bulk delete received but no log channel configured "
                f"guild={payload.guild_id}, channel={payload.channel_id}, count={len(payload.message_ids)}"
            )
            return

        message_ids = [int(mid) for mid in payload.message_ids]
        print(
            "[DeleteLog] Raw bulk delete received "
            f"guild={payload.guild_id}, channel={payload.channel_id}, count={len(message_ids)}"
        )

        snapshot_by_id: Dict[int, Dict[str, Any]] = {}
        no_snapshot_reasons_by_id: Dict[int, str] = {}
        cached_attachments_by_id: Dict[int, List[discord.Attachment]] = {}
        skipped_message_ids: Set[int] = set()
        cached_messages = getattr(payload, "cached_messages", [])
        for message in cached_messages:
            if message.author.bot:
                skipped_message_ids.add(message.id)
                continue
            if message.is_system():
                skipped_message_ids.add(message.id)
                continue
            snapshot = self._build_message_snapshot(message)
            snapshot["message_id"] = message.id
            snapshot["guild_id"] = message.guild.id if message.guild else payload.guild_id
            snapshot["channel_id"] = message.channel.id
            snapshot["channel_name"] = getattr(message.channel, "name", f"channel-{message.channel.id}")
            snapshot["author_id"] = message.author.id
            snapshot["created_at"] = message.created_at
            snapshot_by_id[message.id] = snapshot
            cached_attachments_by_id[message.id] = list(message.attachments)

        uncached_ids = [mid for mid in message_ids if mid not in snapshot_by_id]
        if uncached_ids:
            db_rows = await self.db.get_message_snapshots(uncached_ids)
            for mid, row in db_rows.items():
                snapshot_by_id[mid] = self._build_snapshot_from_db_row(row)
            for mid in uncached_ids:
                if mid not in db_rows:
                    no_snapshot_reasons_by_id[mid] = (
                        "未找到訊息快照；可能原因：訊息建立時 bot 不在線、缺少頻道/討論串權限、"
                        "快取已過期，或訊息建立後很快被刪除。"
                    )

        for message_id in message_ids:
            if message_id in skipped_message_ids:
                print(
                    "[DeleteLog] Skip bot/system message in bulk delete "
                    f"guild={payload.guild_id}, message_id={message_id}"
                )
                continue
            await self._send_deleted_message_log(
                guild_id=payload.guild_id,
                delete_log_channel_id=delete_log_channel_id,
                message_id=message_id,
                fallback_channel_id=payload.channel_id,
                snapshot=snapshot_by_id.get(message_id),
                cached_attachments=cached_attachments_by_id.get(message_id),
                no_snapshot_reason=no_snapshot_reasons_by_id.get(message_id),
            )

    async def on_thread_create(self, thread: discord.Thread) -> None:
        await self._try_join_thread(thread, reason="new-thread")

    def _build_message_snapshot(self, message: discord.Message) -> Dict[str, Any]:
        content = message.content or ""
        attachments = []
        for attachment in message.attachments:
            attachments.append(
                {
                    "filename": attachment.filename,
                    "url": attachment.url,
                    "proxy_url": attachment.proxy_url,
                    "content_type": attachment.content_type or "",
                    "size": attachment.size,
                }
            )

        stickers = []
        for sticker in message.stickers:
            format_name = ""
            format_value = getattr(sticker, "format", None)
            if format_value is not None:
                format_name = to_text(getattr(format_value, "name", format_value)).lower()

            sticker_url = to_text(getattr(sticker, "url", ""))
            sticker_urls = self._build_sticker_asset_urls(sticker.id, format_name)
            if not sticker_url:
                sticker_url = sticker_urls["asset_url"]
            preview_url = sticker_url
            if format_name == "gif" and sticker_urls["preview_url"]:
                preview_url = sticker_urls["preview_url"]
            page_url = sticker_urls["page_url"]

            stickers.append(
                {
                    "id": sticker.id,
                    "name": sticker.name,
                    "format": format_name,
                    "url": sticker_url,
                    "preview_url": preview_url,
                    "page_url": page_url,
                }
            )

        custom_emojis = []
        for match in CUSTOM_EMOJI_REGEX.finditer(content):
            emoji_name = match.group(1)
            emoji_id = match.group(2)
            custom_emojis.append(
                {
                    "name": emoji_name,
                    "id": emoji_id,
                    "animated": match.group(0).startswith("<a:"),
                }
            )

        if isinstance(message.author, discord.Member):
            author_display_name = message.author.display_name
        else:
            author_display_name = message.author.global_name or message.author.name

        avatar_url = ""
        if message.author.display_avatar is not None:
            avatar_url = str(message.author.display_avatar.url)

        mentions_users = [member.id for member in message.mentions]
        mentions_roles = [role.id for role in message.role_mentions]
        mentions_everyone = bool(message.mention_everyone)

        reference_message_id: int | None = None
        reference_channel_id: int | None = None
        reference_author_id: int | None = None
        reply_mention_enabled: bool | None = None

        reference = message.reference
        if reference is not None and reference.message_id is not None:
            reference_message_id = int(reference.message_id)
            if reference.channel_id is not None:
                reference_channel_id = int(reference.channel_id)
            else:
                reference_channel_id = getattr(message.channel, "id", None)

            resolved = getattr(reference, "resolved", None)
            if isinstance(resolved, discord.Message):
                reference_author_id = resolved.author.id
            cached_reference = getattr(reference, "cached_message", None)
            if reference_author_id is None and isinstance(cached_reference, discord.Message):
                reference_author_id = cached_reference.author.id
            if reference_author_id is not None:
                # `message.mentions` reflects actual mention targets better than raw text parsing.
                reply_mention_enabled = reference_author_id in mentions_users

        return {
            "content": content,
            "author_display_name": author_display_name,
            "author_avatar_url": avatar_url,
            "attachments": attachments,
            "stickers": stickers,
            "custom_emojis": custom_emojis,
            "reference_message_id": reference_message_id,
            "reference_channel_id": reference_channel_id,
            "reference_author_id": reference_author_id,
            "reply_mention_enabled": reply_mention_enabled,
            "mentions_users": mentions_users,
            "mentions_roles": mentions_roles,
            "mentions_everyone": mentions_everyone,
        }

    def _build_sticker_asset_urls(self, sticker_id: int, format_name: str) -> Dict[str, str]:
        if sticker_id <= 0:
            return {"asset_url": "", "preview_url": "", "page_url": ""}

        base = f"https://media.discordapp.net/stickers/{sticker_id}"
        asset_url = f"{base}.png"
        preview_url = asset_url
        if format_name in {"gif"}:
            asset_url = f"{base}.gif"
            preview_url = f"{base}.png"
        elif format_name in {"lottie"}:
            asset_url = f"{base}.json"
            preview_url = ""

        return {
            "asset_url": asset_url,
            "preview_url": preview_url,
            "page_url": f"https://discord.com/stickers/{sticker_id}",
        }

    def _build_snapshot_from_db_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        def parse_json_list(raw: Any) -> List[Any]:
            if raw is None:
                return []
            try:
                parsed = json.loads(str(raw))
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []

        def parse_json_int_list(raw: Any) -> List[int]:
            parsed = parse_json_list(raw)
            numbers: List[int] = []
            for item in parsed:
                try:
                    numbers.append(int(item))
                except (TypeError, ValueError):
                    continue
            return numbers

        def parse_optional_int(raw: Any) -> int | None:
            if raw is None:
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        def parse_optional_bool(raw: Any) -> bool | None:
            if raw is None:
                return None
            if isinstance(raw, bool):
                return raw
            text = to_text(raw).strip().lower()
            if text in {"1", "true", "t", "yes", "y", "on"}:
                return True
            if text in {"0", "false", "f", "no", "n", "off"}:
                return False
            return None

        return {
            "message_id": int(row.get("id", 0)),
            "guild_id": int(row.get("guild_id", 0)),
            "channel_id": int(row.get("channel_id", 0)),
            "channel_name": to_text(row.get("channel_name")) or "unknown-channel",
            "author_id": int(row.get("author_id", 0)),
            "created_at": row.get("created_at"),
            "content": to_text(row.get("content")),
            "author_display_name": to_text(row.get("author_display_name")),
            "author_avatar_url": to_text(row.get("author_avatar_url")),
            "attachments": parse_json_list(row.get("attachments_json")),
            "stickers": parse_json_list(row.get("stickers_json")),
            "custom_emojis": parse_json_list(row.get("custom_emojis_json")),
            "reference_message_id": parse_optional_int(row.get("reference_message_id")),
            "reference_channel_id": parse_optional_int(row.get("reference_channel_id")),
            "reference_author_id": parse_optional_int(row.get("reference_author_id")),
            "reply_mention_enabled": parse_optional_bool(row.get("reply_mention_enabled")),
            "mentions_users": parse_json_int_list(row.get("mentions_users_json")),
            "mentions_roles": parse_json_int_list(row.get("mentions_roles_json")),
            "mentions_everyone": bool(row.get("mentions_everyone", False)),
        }

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

    async def _send_deleted_message_log(
        self,
        guild_id: int,
        delete_log_channel_id: int,
        message_id: int,
        fallback_channel_id: int | None,
        snapshot: Dict[str, Any] | None,
        cached_attachments: List[discord.Attachment] | None = None,
        no_snapshot_reason: str | None = None,
    ) -> None:
        channel_obj = self.get_channel(delete_log_channel_id)
        if not isinstance(channel_obj, discord.TextChannel):
            try:
                fetched = await self.fetch_channel(delete_log_channel_id)
                if isinstance(fetched, discord.TextChannel):
                    channel_obj = fetched
                else:
                    print(
                        "[DeleteLog] Configured channel is not a text channel "
                        f"guild={guild_id}, channel={delete_log_channel_id}"
                    )
                    return
            except discord.HTTPException as exc:
                print(
                    "[DeleteLog] Failed to resolve delete log channel "
                    f"guild={guild_id}, channel={delete_log_channel_id}: {exc}"
                )
                return

        deleted_at = datetime.now(timezone.utc)

        author_id = int(snapshot.get("author_id", 0)) if snapshot else 0
        author_display_name = to_text(snapshot.get("author_display_name")) if snapshot else ""
        author_avatar_url = to_text(snapshot.get("author_avatar_url")) if snapshot else ""
        content = to_text(snapshot.get("content")) if snapshot else ""
        channel_id = int(snapshot.get("channel_id", 0)) if snapshot else 0
        if channel_id == 0 and fallback_channel_id is not None:
            channel_id = fallback_channel_id
        created_at = snapshot.get("created_at") if snapshot else None
        attachments = snapshot.get("attachments", []) if snapshot else []
        stickers = snapshot.get("stickers", []) if snapshot else []
        custom_emojis = snapshot.get("custom_emojis", []) if snapshot else []
        reference_message_id = int(snapshot.get("reference_message_id") or 0) if snapshot else 0
        reference_channel_id = int(snapshot.get("reference_channel_id") or 0) if snapshot else 0
        reference_author_id = int(snapshot.get("reference_author_id") or 0) if snapshot else 0
        reply_mention_enabled = snapshot.get("reply_mention_enabled") if snapshot else None
        mentions_users = snapshot.get("mentions_users", []) if snapshot else []
        mentions_roles = snapshot.get("mentions_roles", []) if snapshot else []
        mentions_everyone = bool(snapshot.get("mentions_everyone", False)) if snapshot else False

        if snapshot is None:
            print(
                "[DeleteLog] No snapshot found for deleted message "
                f"guild={guild_id}, message_id={message_id}, fallback_channel={fallback_channel_id}"
            )
            if not no_snapshot_reason:
                no_snapshot_reason = (
                    "未找到訊息快照；可能原因：訊息建立時 bot 不在線、缺少頻道/討論串權限、"
                    "快取已過期，或訊息建立後很快被刪除。"
                )

        if created_at is not None and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = None

        guild = self.get_guild(guild_id)
        if author_id and guild is not None and (
            not author_display_name or author_display_name.startswith("user-")
        ):
            member = guild.get_member(author_id)
            if member is None:
                try:
                    member = await guild.fetch_member(author_id)
                except discord.HTTPException:
                    member = None
            if member is not None:
                author_display_name = member.display_name
                if not author_avatar_url:
                    author_avatar_url = str(member.display_avatar.url)

        if not author_display_name:
            author_display_name = f"user-{author_id}" if author_id else "未知使用者"

        title = "訊息刪除紀錄"
        embed = discord.Embed(
            title=title,
            color=discord.Color.red(),
        )
        embed.set_author(
            name=author_display_name,
            icon_url=author_avatar_url if author_avatar_url else None,
        )

        channel_name = to_text(snapshot.get("channel_name")) if snapshot else ""
        if not channel_name and channel_id:
            channel_name = f"<#{channel_id}>"
        if channel_id:
            embed.add_field(name="頻道", value=f"<#{channel_id}>", inline=False)
        elif channel_name:
            embed.add_field(name="頻道", value=channel_name, inline=False)

        embed.add_field(
            name="訊息內容",
            value=truncate_text(content, 1000)
            if content.strip()
            else (
                "(無文字內容，且未留存附件/貼圖快照)"
                if not attachments and not stickers and not custom_emojis
                else "(無文字內容)"
            ),
            inline=False,
        )

        if snapshot is None and no_snapshot_reason:
            embed.add_field(
                name="快照狀態",
                value=truncate_text(no_snapshot_reason, 1000),
                inline=False,
            )

        if reference_message_id:
            if reply_mention_enabled is None and reference_author_id:
                reply_mention_enabled = reference_author_id in mentions_users

            if reply_mention_enabled is True:
                reply_mention_text = "開啟"
            elif reply_mention_enabled is False:
                reply_mention_text = "關閉"
            else:
                reply_mention_text = "未知（無法判定）"
            referenced_preview = "(無法取得，可能未留存或已刪除)"
            reference_snapshot = await self.db.get_message_snapshot(reference_message_id)
            if reference_snapshot is not None:
                reference_data = self._build_snapshot_from_db_row(reference_snapshot)
                if not reference_author_id:
                    reference_author_id = int(reference_data.get("author_id", 0))
                referenced_content = to_text(reference_data.get("content")).strip()
                reference_attachments = reference_data.get("attachments", [])
                reference_stickers = reference_data.get("stickers", [])
                reference_custom_emojis = reference_data.get("custom_emojis", [])
                if referenced_content:
                    referenced_preview = truncate_text(referenced_content, 240)
                elif reference_attachments or reference_stickers or reference_custom_emojis:
                    referenced_preview = "(無文字內容，含附件/貼圖/表情)"
                else:
                    referenced_preview = "(無文字內容)"

            reply_info_lines = []
            if reference_author_id:
                reply_info_lines.append(f"回覆對象: <@{reference_author_id}>")
            else:
                reply_info_lines.append("回覆對象: (未知)")
            reply_info_lines.append(f"回覆 mention: {reply_mention_text}")
            reply_channel_id = reference_channel_id or channel_id
            if reply_channel_id:
                reply_jump_url = (
                    f"https://discord.com/channels/{guild_id}/{reply_channel_id}/{reference_message_id}"
                )
                reply_info_lines.append(f"[原始訊息連結]({reply_jump_url})")
            embed.add_field(name="回覆資訊", value=truncate_text("\n".join(reply_info_lines), 1000), inline=False)

            quoted_reply_preview = "\n".join(f"> {line}" for line in referenced_preview.splitlines()) or "> (無文字內容)"
            embed.add_field(
                name="回覆訊息",
                value=truncate_text(quoted_reply_preview, 1000),
                inline=False,
            )

        time_lines = [f"刪除：<t:{int(deleted_at.timestamp())}:f>"]
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            time_lines.append(f"原訊息：<t:{int(created_at.timestamp())}:f>")
        embed.add_field(
            name="時間",
            value="\n".join(time_lines),
            inline=False,
        )

        if stickers:
            sticker_lines = []
            for index, item in enumerate(stickers):
                if index >= 6:
                    sticker_lines.append(f"... and {len(stickers) - 6} more")
                    break
                name = to_text(item.get("name")) or "sticker"
                sticker_id = to_text(item.get("id"))
                format_name_raw = to_text(item.get("format")).lower()
                format_name = format_name_raw.upper()
                sticker_url = to_text(item.get("url"))
                sticker_preview_url = to_text(item.get("preview_url"))
                sticker_page_url = to_text(item.get("page_url"))

                sticker_id_int = 0
                if sticker_id.isdigit():
                    sticker_id_int = int(sticker_id)
                fallback_urls = self._build_sticker_asset_urls(sticker_id_int, format_name_raw)
                open_url = (
                    sticker_preview_url
                    or sticker_url
                    or fallback_urls["preview_url"]
                    or fallback_urls["asset_url"]
                    or sticker_page_url
                    or fallback_urls["page_url"]
                )

                line = name
                if sticker_id:
                    line = f"{line} (`{sticker_id}`)"
                if format_name:
                    line = f"{line} [{format_name}]"
                if open_url:
                    line = f"{line} [open]({open_url})"
                sticker_lines.append(line)
            if sticker_lines:
                embed.add_field(name="貼圖", value=truncate_text("\n".join(sticker_lines), 1000), inline=False)

        if custom_emojis:
            emoji_items = []
            for item in custom_emojis:
                name = to_text(item.get("name"))
                emoji_id = to_text(item.get("id"))
                if name and emoji_id:
                    emoji_items.append(f"{name} (`{emoji_id}`)")
                elif name:
                    emoji_items.append(name)
            if emoji_items:
                embed.add_field(
                    name="自訂表情符號",
                    value=truncate_text(", ".join(emoji_items), 1000),
                    inline=False,
                )

        preview_image_url = ""
        upload_files: List[discord.File] = []
        uploaded_image_filename = ""
        if cached_attachments:
            upload_files, uploaded_image_filename = await self._build_deleted_log_files(cached_attachments)

        if attachments:
            lines = []
            for index, item in enumerate(attachments):
                if index >= 8:
                    lines.append(f"... and {len(attachments) - 8} more")
                    break
                filename = to_text(item.get("filename")) or "attachment"
                url = to_text(item.get("url")) or to_text(item.get("proxy_url"))
                content_type = to_text(item.get("content_type"))
                line = f"[{filename}]({url})" if url else filename
                if content_type:
                    line = f"{line} ({content_type})"
                lines.append(line)
            if lines:
                embed.add_field(name="附件", value=truncate_text("\n".join(lines), 1000), inline=False)

            for item in attachments:
                content_type = to_text(item.get("content_type")).lower()
                url = to_text(item.get("url")) or to_text(item.get("proxy_url"))
                filename = to_text(item.get("filename")).lower()
                if not url:
                    continue
                if content_type.startswith("image/") or filename.endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".webp")
                ):
                    preview_image_url = url
                    break

        if uploaded_image_filename:
            preview_image_url = f"attachment://{uploaded_image_filename}"

        if not preview_image_url and stickers:
            for item in stickers:
                sticker_id = to_text(item.get("id"))
                format_name_raw = to_text(item.get("format")).lower()
                sticker_preview_url = to_text(item.get("preview_url"))
                sticker_url = to_text(item.get("url"))

                sticker_id_int = int(sticker_id) if sticker_id.isdigit() else 0
                fallback_urls = self._build_sticker_asset_urls(sticker_id_int, format_name_raw)
                candidate = (
                    sticker_preview_url
                    or sticker_url
                    or fallback_urls["preview_url"]
                    or fallback_urls["asset_url"]
                )
                if candidate and not candidate.endswith(".json"):
                    preview_image_url = candidate
                    break

        if preview_image_url:
            embed.set_image(url=preview_image_url)

        if attachments and not upload_files:
            embed.add_field(
                name="附件提示",
                value="附件連結可能因 Discord CDN 時效而過期，建議儘快查看。",
                inline=False,
            )

        embed.set_footer(text=f"message_id: {message_id}")

        try:
            send_kwargs: Dict[str, Any] = {"embed": embed}
            if upload_files:
                send_kwargs["files"] = upload_files
            await channel_obj.send(**send_kwargs)
        except discord.HTTPException as exc:
            print(
                "[DeleteLog] Failed to send delete log message "
                f"guild={guild_id}, channel={delete_log_channel_id}, message_id={message_id}: {exc}"
            )

    async def _build_deleted_log_files(
        self,
        cached_attachments: List[discord.Attachment],
    ) -> Tuple[List[discord.File], str]:
        files: List[discord.File] = []
        image_filename = ""
        max_file_count = 4
        max_file_size = 8 * 1024 * 1024

        for attachment in cached_attachments[:max_file_count]:
            if attachment.size > max_file_size:
                continue
            try:
                file = await attachment.to_file(use_cached=True)
                files.append(file)
                is_image = (attachment.content_type or "").lower().startswith("image/") or attachment.filename.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".webp")
                )
                if not image_filename and is_image:
                    image_filename = file.filename
            except discord.HTTPException:
                continue
            except Exception:
                continue

        return files, image_filename

    async def _run_startup_tasks(self) -> None:
        await self._auto_join_existing_threads()
        print(
            "[StartupConfig] "
            f"history_backfill_on_startup={self.history_backfill_on_startup}, "
            f"history_backfill_days={self.history_backfill_days}, "
            f"cleanup_on_startup={self.cleanup_on_startup}, cleanup_days={self.cleanup_days}"
        )

        if not self.startup_cleanup_done and self.cleanup_on_startup:
            self.startup_cleanup_done = True
            await self._run_startup_cleanup_once()

        if not self.startup_backfill_done and self.history_backfill_on_startup:
            self.startup_backfill_done = True
            await self._run_history_backfill_once()
        else:
            print("[HistoryBackfill] Skipped by config or already handled.")

    async def _run_startup_cleanup_once(self) -> None:
        from_time = datetime.now(timezone.utc) - timedelta(days=self.cleanup_days)
        print(
            "[StartupCleanup] Start "
            f"window={self.cleanup_days}d, from={from_time.isoformat()}"
        )
        deleted_count = await self.db.cleanup_empty_snapshot_messages(from_time=from_time)
        print(f"[StartupCleanup] Done deleted_rows={deleted_count}")

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
                if message.is_system():
                    continue
                snapshot = self._build_message_snapshot(message)
                ok = await self.db.insert_message(
                    message_id=message.id,
                    guild_id=guild_id,
                    channel_id=message.channel.id,
                    channel_name=channel_name,
                    author_id=message.author.id,
                    created_at=message.created_at,
                    content=snapshot["content"],
                    author_display_name=snapshot["author_display_name"],
                    author_avatar_url=snapshot["author_avatar_url"],
                    attachments_json=json.dumps(snapshot["attachments"], ensure_ascii=False),
                    stickers_json=json.dumps(snapshot["stickers"], ensure_ascii=False),
                    custom_emojis_json=json.dumps(snapshot["custom_emojis"], ensure_ascii=False),
                    reference_message_id=snapshot["reference_message_id"],
                    reference_channel_id=snapshot["reference_channel_id"],
                    reference_author_id=snapshot["reference_author_id"],
                    reply_mention_enabled=snapshot["reply_mention_enabled"],
                    mentions_users_json=json.dumps(snapshot["mentions_users"], ensure_ascii=False),
                    mentions_roles_json=json.dumps(snapshot["mentions_roles"], ensure_ascii=False),
                    mentions_everyone=bool(snapshot["mentions_everyone"]),
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


class TabetaiDrawView(discord.ui.View):
    def __init__(
        self,
        bot: HotmapBot,
        guild_id: int,
        user_id: int,
        candidates: List[str],
        recent_meals: List[str],
        initial_choice: str,
        relaxed_rule: bool,
    ) -> None:
        super().__init__(timeout=180)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.candidates = list(candidates)
        self.recent_meals = list(recent_meals)
        self.current_choice = initial_choice
        self.relaxed_rule = relaxed_rule
        self.excluded_meals: Set[str] = set()
        self.message: discord.Message | None = None
        self.is_rolling = False

    def _session_key(self) -> Tuple[int, int]:
        return (self.guild_id, self.user_id)

    def _release_session(self) -> None:
        self.bot.active_tabetai_sessions.discard(self._session_key())

    def _build_result_embed(self, confirmed: bool = False) -> discord.Embed:
        embed = discord.Embed(
            title="食べたい抽選",
            color=discord.Color.orange() if not confirmed else discord.Color.green(),
        )
        embed.add_field(
            name="🎯 抽選結果",
            value=f"```text\n{self.current_choice}\n```",
            inline=False,
        )
        embed.add_field(
            name="使用者",
            value=f"<@{self.user_id}>",
            inline=False,
        )

        if self.recent_meals:
            embed.add_field(
                name=f"最近 {TABETAI_RECENT_MEAL_COUNT} 餐",
                value="、".join(self.recent_meals[:TABETAI_RECENT_MEAL_COUNT]),
                inline=False,
            )
        else:
            embed.add_field(
                name=f"最近 {TABETAI_RECENT_MEAL_COUNT} 餐",
                value="（尚無紀錄）",
                inline=False,
            )

        if confirmed:
            embed.add_field(name="狀態", value="✅ 選好了 趕快去吃！", inline=False)
        else:
            status = "❗ 本輪可選項不足，已暫時放寬不重複限制。" if self.relaxed_rule else "請按 ✅ 確認，或按 ❌ 重抽。"
            embed.add_field(name="狀態", value=status, inline=False)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "只有發起抽籤的人可以操作這個按鈕。",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        self._release_session()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="✅ 確認", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.bot.db.insert_meal_selection(
            guild_id=self.guild_id,
            user_id=self.user_id,
            meal_name=self.current_choice,
        )
        self._release_session()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(
            embed=self._build_result_embed(confirmed=True),
            view=self,
        )

    @discord.ui.button(label="❌ 重抽", style=discord.ButtonStyle.danger)
    async def redraw_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.is_rolling:
            await interaction.response.send_message(
                "正在抽選中，請稍候。",
                ephemeral=True,
            )
            return

        self.excluded_meals.add(self.current_choice)
        next_choice, relaxed_rule = pick_tabetai_choice(
            candidates=self.candidates,
            recent_meals=self.recent_meals,
            excluded_meals=self.excluded_meals,
        )
        if not next_choice:
            await interaction.response.send_message(
                "目前沒有可抽取的品項，請稍後再試。",
                ephemeral=True,
            )
            return

        self.is_rolling = True
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        target_message = self.message or interaction.message
        if target_message is None:
            self.is_rolling = False
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = False
            await interaction.response.send_message(
                "抽選面板狀態異常，請重新輸入 /tabetai。",
                ephemeral=True,
            )
            return
        self.message = target_message

        redraw_success = False
        redraw_error: Exception | None = None
        try:
            first_frame = build_tabetai_animation_embed(
                candidates=self.candidates,
                step=1,
                total_steps=TABETAI_ANIMATION_STEPS,
                redraw=True,
            )
            await interaction.response.edit_message(embed=first_frame, view=self)

            for step in range(2, TABETAI_ANIMATION_STEPS + 1):
                await asyncio.sleep(TABETAI_ANIMATION_DELAY_SEC)
                frame_embed = build_tabetai_animation_embed(
                    candidates=self.candidates,
                    step=step,
                    total_steps=TABETAI_ANIMATION_STEPS,
                    redraw=True,
                )
                await target_message.edit(embed=frame_embed, view=self)

            self.current_choice = next_choice
            self.relaxed_rule = relaxed_rule
            redraw_success = True
        except Exception as exc:
            redraw_error = exc
        finally:
            self.is_rolling = False

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = False

        if redraw_success:
            await target_message.edit(
                embed=self._build_result_embed(confirmed=False),
                view=self,
            )
            return

        try:
            await target_message.edit(view=self)
        except discord.HTTPException:
            pass
        if redraw_error is not None:
            print(f"[Tabetai] redraw animation failed: {redraw_error}")
        await interaction.followup.send(
            "重抽動畫發生問題，按鈕已恢復，請再試一次。",
            ephemeral=True,
        )


class TabetaiRemoveView(discord.ui.View):
    def __init__(
        self,
        bot: HotmapBot,
        guild_id: int,
        user_id: int,
        meal_options: List[str],
    ) -> None:
        super().__init__(timeout=180)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.meal_options = list(meal_options)
        self.page_index = 0
        self.page_size = 25
        self.message: discord.Message | None = None
        self._refresh_components()

    def _max_page_index(self) -> int:
        if not self.meal_options:
            return 0
        return (len(self.meal_options) - 1) // self.page_size

    def _current_page_items(self) -> List[str]:
        start = self.page_index * self.page_size
        end = start + self.page_size
        return self.meal_options[start:end]

    def _refresh_components(self) -> None:
        self.clear_items()

        page_items = self._current_page_items()
        if page_items:
            options = [
                discord.SelectOption(
                    label=truncate_text(item, 100),
                    value=item,
                )
                for item in page_items
            ]
            select = discord.ui.Select(
                placeholder="選擇要移除的餐點",
                min_values=1,
                max_values=1,
                options=options,
            )

            async def on_select(interaction: discord.Interaction) -> None:
                selected_name = select.values[0]
                removed = await self.bot.db.remove_meal_option(self.guild_id, selected_name)
                self.meal_options = await self.bot.db.get_meal_options(self.guild_id)
                self.page_index = min(self.page_index, self._max_page_index())
                self._refresh_components()

                if removed:
                    message = f"已移除餐點：`{selected_name}`"
                else:
                    message = f"移除失敗或項目不存在：`{selected_name}`"

                await interaction.response.edit_message(
                    embed=self.build_embed(message),
                    view=self,
                )

            select.callback = on_select
            self.add_item(select)

        prev_button = discord.ui.Button(
            label="⬅️ 上一頁",
            style=discord.ButtonStyle.secondary,
            disabled=not self.meal_options or self.page_index <= 0,
        )

        async def on_prev(interaction: discord.Interaction) -> None:
            self.page_index = max(0, self.page_index - 1)
            self._refresh_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        prev_button.callback = on_prev
        self.add_item(prev_button)

        next_button = discord.ui.Button(
            label="下一頁 ➡️",
            style=discord.ButtonStyle.secondary,
            disabled=not self.meal_options or self.page_index >= self._max_page_index(),
        )

        async def on_next(interaction: discord.Interaction) -> None:
            self.page_index = min(self._max_page_index(), self.page_index + 1)
            self._refresh_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        next_button.callback = on_next
        self.add_item(next_button)

        close_button = discord.ui.Button(
            label="完成",
            style=discord.ButtonStyle.success,
        )

        async def on_close(interaction: discord.Interaction) -> None:
            self.stop()
            for item in self.children:
                if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                    item.disabled = True
            await interaction.response.edit_message(embed=self.build_embed("已關閉移除面板。"), view=self)

        close_button.callback = on_close
        self.add_item(close_button)

    def build_embed(self, status_message: str = "請從下拉選單選擇要移除的餐點。") -> discord.Embed:
        embed = discord.Embed(
            title="tabetai 餐點清單移除",
            color=discord.Color.orange(),
            description=status_message,
        )
        total = len(self.meal_options)
        if total == 0:
            embed.add_field(name="目前清單", value="（無資料）", inline=False)
            embed.add_field(name="提示", value="下一次使用 /tabetai 會自動載入完整預設清單。", inline=False)
            return embed

        page_items = self._current_page_items()
        page_text = "\n".join(f"- {item}" for item in page_items) or "（無資料）"
        embed.add_field(name="本頁餐點", value=truncate_text(page_text, 1000), inline=False)
        embed.add_field(
            name="頁面",
            value=f"{self.page_index + 1}/{self._max_page_index() + 1}（共 {total} 項）",
            inline=False,
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "只有發起指令的人可以操作這個面板。",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class TabetaiHistoryClearView(discord.ui.View):
    def __init__(
        self,
        bot: HotmapBot,
        guild_id: int,
        user_id: int,
        entries: List[Tuple[int, str, datetime]],
    ) -> None:
        super().__init__(timeout=180)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.entries = list(entries)
        self.page_index = 0
        self.page_size = 25
        self.message: discord.Message | None = None
        self._refresh_components()

    def _max_page_index(self) -> int:
        if not self.entries:
            return 0
        return (len(self.entries) - 1) // self.page_size

    def _current_page_entries(self) -> List[Tuple[int, str, datetime]]:
        start = self.page_index * self.page_size
        end = start + self.page_size
        return self.entries[start:end]

    def _format_time_text(self, selected_at: datetime) -> str:
        value = selected_at
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.strftime("%Y-%m-%d %H:%M UTC")

    def _refresh_components(self) -> None:
        self.clear_items()

        page_entries = self._current_page_entries()
        if page_entries:
            options = []
            for entry_id, meal_name, selected_at in page_entries:
                options.append(
                    discord.SelectOption(
                        label=truncate_text(meal_name, 100),
                        value=str(entry_id),
                        description=truncate_text(self._format_time_text(selected_at), 100),
                    )
                )
            select = discord.ui.Select(
                placeholder="選擇要清除的抽選紀錄",
                min_values=1,
                max_values=1,
                options=options,
            )

            async def on_select(interaction: discord.Interaction) -> None:
                selected_entry_id = int(select.values[0])
                removed = await self.bot.db.delete_meal_history_entry(
                    guild_id=self.guild_id,
                    user_id=self.user_id,
                    entry_id=selected_entry_id,
                )
                self.entries = await self.bot.db.get_meal_history_entries(
                    guild_id=self.guild_id,
                    user_id=self.user_id,
                    limit=100,
                )
                self.page_index = min(self.page_index, self._max_page_index())
                self._refresh_components()

                if removed:
                    status = f"已刪除抽選紀錄（id={selected_entry_id}）。"
                else:
                    status = f"刪除失敗或紀錄不存在（id={selected_entry_id}）。"
                await interaction.response.edit_message(
                    embed=self.build_embed(status),
                    view=self,
                )

            select.callback = on_select
            self.add_item(select)

        prev_button = discord.ui.Button(
            label="⬅️ 上一頁",
            style=discord.ButtonStyle.secondary,
            disabled=not self.entries or self.page_index <= 0,
        )

        async def on_prev(interaction: discord.Interaction) -> None:
            self.page_index = max(0, self.page_index - 1)
            self._refresh_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        prev_button.callback = on_prev
        self.add_item(prev_button)

        next_button = discord.ui.Button(
            label="下一頁 ➡️",
            style=discord.ButtonStyle.secondary,
            disabled=not self.entries or self.page_index >= self._max_page_index(),
        )

        async def on_next(interaction: discord.Interaction) -> None:
            self.page_index = min(self._max_page_index(), self.page_index + 1)
            self._refresh_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        next_button.callback = on_next
        self.add_item(next_button)

        close_button = discord.ui.Button(
            label="完成",
            style=discord.ButtonStyle.success,
        )

        async def on_close(interaction: discord.Interaction) -> None:
            self.stop()
            for item in self.children:
                if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                    item.disabled = True
            await interaction.response.edit_message(
                embed=self.build_embed("已關閉紀錄清除面板。"),
                view=self,
            )

        close_button.callback = on_close
        self.add_item(close_button)

    def build_embed(self, status_message: str = "請從下拉選單選擇要清除的紀錄。") -> discord.Embed:
        embed = discord.Embed(
            title="食べたい抽選紀錄清除",
            color=discord.Color.orange(),
            description=status_message,
        )
        if not self.entries:
            embed.add_field(name="目前紀錄", value="（無資料）", inline=False)
            return embed

        page_entries = self._current_page_entries()
        lines: List[str] = []
        for entry_id, meal_name, selected_at in page_entries:
            ts = selected_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            lines.append(f"- {meal_name} · <t:{int(ts.timestamp())}:f> (`{entry_id}`)")
        embed.add_field(name="本頁紀錄", value=truncate_text("\n".join(lines), 1000), inline=False)
        embed.add_field(
            name="頁面",
            value=f"{self.page_index + 1}/{self._max_page_index() + 1}（共 {len(self.entries)} 筆）",
            inline=False,
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "只有發起指令的人可以操作這個面板。",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class ChannelsTopUserPaginationView(discord.ui.View):
    def __init__(
        self,
        *,
        guild: discord.Guild | None,
        invoker_user_id: int,
        days: int,
        min_messages: int,
        rows: List[Tuple[int, str, int, int]],
    ) -> None:
        super().__init__(timeout=300)
        self.guild = guild
        self.invoker_user_id = invoker_user_id
        self.days = days
        self.min_messages = min_messages
        self.rows = rows
        self.page_size = CHANNEL_TOP_USER_PAGE_SIZE
        self.page_index = 0
        self.message: discord.Message | None = None
        self._sync_buttons()

    def _max_page_index(self) -> int:
        if not self.rows:
            return 0
        return (len(self.rows) - 1) // self.page_size

    def _sync_buttons(self) -> None:
        self.prev_page_button.disabled = self.page_index <= 0
        self.next_page_button.disabled = self.page_index >= self._max_page_index()

    def _current_rows(self) -> List[Tuple[int, str, int, int]]:
        start = self.page_index * self.page_size
        end = start + self.page_size
        return self.rows[start:end]

    def build_page_text(self) -> str:
        lines = [
            f"Here is each channel's top active user in last {self.days} day(s).",
            f"Threshold: >= {self.min_messages} messages.",
            f"Page {self.page_index + 1}/{self._max_page_index() + 1} (channels: {len(self.rows)}).",
            "",
        ]
        start_rank = self.page_index * self.page_size + 1
        for offset, (channel_id, channel_name, author_id, count) in enumerate(self._current_rows()):
            rank = start_rank + offset
            channel_obj: discord.abc.GuildChannel | discord.Thread | None = None
            if self.guild is not None:
                channel_obj = self.guild.get_channel(channel_id)
                if channel_obj is None:
                    channel_obj = self.guild.get_thread(channel_id)
            if channel_obj is not None:
                channel_text = f"<#{channel_id}>"
            else:
                channel_label = clean_channel_label_for_chart(channel_name) or "unknown-channel"
                channel_text = f"<#{channel_id}> ({channel_label})"

            member_obj = self.guild.get_member(author_id) if self.guild is not None else None
            if member_obj is not None:
                user_text = f"<@{author_id}>"
            else:
                user_text = f"<@{author_id}> (unknown-user)"
            lines.append(f"{rank}. {channel_text}: {user_text} - {format_count(count)}")
        return "\n".join(lines)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_user_id:
            await interaction.response.send_message(
                "Only the command invoker can switch pages.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
    async def prev_page_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = max(0, self.page_index - 1)
        self._sync_buttons()
        await interaction.response.edit_message(
            content=self.build_page_text(),
            view=self,
            allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False),
        )

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.secondary)
    async def next_page_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.page_index = min(self._max_page_index(), self.page_index + 1)
        self._sync_buttons()
        await interaction.response.edit_message(
            content=self.build_page_text(),
            view=self,
            allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False),
        )

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


def build_tabetai_command(bot: HotmapBot) -> app_commands.Command:
    @app_commands.command(
        name="tabetai",
        description="Draw a meal suggestion with confirm/redraw buttons.",
    )
    @app_commands.guild_only()
    async def tabetai(interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        guild = interaction.guild
        if guild_id is None or guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        user_id = interaction.user.id
        session_key = (guild_id, user_id)
        if session_key in bot.active_tabetai_sessions:
            await interaction.response.send_message(
                "你已經有一個進行中的抽籤，請先完成目前這輪。",
                ephemeral=True,
            )
            return

        bot.active_tabetai_sessions.add(session_key)

        try:
            candidates = await bot.db.ensure_meal_options(guild_id, TABETAI_FOODS)
            recent_meals = await bot.db.get_recent_meal_selections(
                guild_id=guild_id,
                user_id=user_id,
                limit=TABETAI_RECENT_MEAL_COUNT,
            )

            choice, relaxed_rule = pick_tabetai_choice(
                candidates=candidates,
                recent_meals=recent_meals,
                excluded_meals=set(),
            )
            if not choice:
                bot.active_tabetai_sessions.discard(session_key)
                await interaction.response.send_message(
                    "目前沒有可抽取的品項，請先補上品項設定。",
                    ephemeral=True,
                )
                return

            rolling_embed = build_tabetai_animation_embed(
                candidates=candidates,
                step=1,
                total_steps=TABETAI_ANIMATION_STEPS,
                redraw=False,
            )
            await interaction.response.send_message(embed=rolling_embed)
            message = await interaction.original_response()

            for step in range(2, TABETAI_ANIMATION_STEPS + 1):
                await asyncio.sleep(TABETAI_ANIMATION_DELAY_SEC)
                rolling_embed = build_tabetai_animation_embed(
                    candidates=candidates,
                    step=step,
                    total_steps=TABETAI_ANIMATION_STEPS,
                    redraw=False,
                )
                await message.edit(embed=rolling_embed, view=None)
            if TABETAI_ANIMATION_STEPS == 1:
                await message.edit(embed=rolling_embed, view=None)

            if TABETAI_ANIMATION_STEPS > 1:
                await asyncio.sleep(TABETAI_ANIMATION_DELAY_SEC)

            view = TabetaiDrawView(
                bot=bot,
                guild_id=guild_id,
                user_id=user_id,
                candidates=candidates,
                recent_meals=recent_meals,
                initial_choice=choice,
                relaxed_rule=relaxed_rule,
            )
            view.message = message
            await message.edit(embed=view._build_result_embed(confirmed=False), view=view)
        except Exception:
            bot.active_tabetai_sessions.discard(session_key)
            raise

    return tabetai


def build_tabetai_clear_command(bot: HotmapBot) -> app_commands.Command:
    @app_commands.command(
        name="tabetai_clear",
        description="Remove selected tabetai history entries.",
    )
    @app_commands.guild_only()
    async def tabetai_clear(interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        user_id = interaction.user.id
        entries = await bot.db.get_meal_history_entries(
            guild_id=guild_id,
            user_id=user_id,
            limit=100,
        )
        if not entries:
            await interaction.response.send_message(
                "你目前沒有抽選紀錄可清除。",
                ephemeral=True,
            )
            return

        view = TabetaiHistoryClearView(
            bot=bot,
            guild_id=guild_id,
            user_id=user_id,
            entries=entries,
        )
        await interaction.response.send_message(
            embed=view.build_embed(),
            view=view,
            ephemeral=True,
        )
        view.message = await interaction.original_response()

    return tabetai_clear


def build_tabetai_add_command(bot: HotmapBot) -> app_commands.Command:
    @app_commands.command(
        name="tabetai_add",
        description="Add one meal option to tabetai list.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(meal_name="Meal name to add")
    async def tabetai_add(
        interaction: discord.Interaction,
        meal_name: app_commands.Range[str, 1, 60],
    ) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need server administrator permission to use this command.",
                ephemeral=True,
            )
            return

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        normalized_name = meal_name.strip()
        if not normalized_name:
            await interaction.response.send_message(
                "meal_name cannot be empty.",
                ephemeral=True,
            )
            return

        existing_options = await bot.db.ensure_meal_options(guild_id, TABETAI_FOODS)
        normalized_key = normalized_name.casefold()
        for option in existing_options:
            if option.strip().casefold() == normalized_key:
                await interaction.response.send_message(
                    f"餐點已存在：`{option}`",
                    ephemeral=True,
                )
                return

        inserted = await bot.db.add_meal_option(guild_id, normalized_name)
        current_options = await bot.db.get_meal_options(guild_id)
        if inserted:
            await interaction.response.send_message(
                f"已新增餐點：`{normalized_name}`\n目前清單共 {len(current_options)} 項。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"餐點已存在：`{normalized_name}`",
            ephemeral=True,
        )

    return tabetai_add


def build_tabetai_remove_command(bot: HotmapBot) -> app_commands.Command:
    @app_commands.command(
        name="tabetai_remove",
        description="Remove meal options (by name or interactive picker).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(meal_name="Meal name to remove (optional)")
    async def tabetai_remove(
        interaction: discord.Interaction,
        meal_name: app_commands.Range[str, 1, 60] | None = None,
    ) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need server administrator permission to use this command.",
                ephemeral=True,
            )
            return

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        options = await bot.db.ensure_meal_options(guild_id, TABETAI_FOODS)
        if not options:
            await interaction.response.send_message(
                "目前沒有可移除的餐點。",
                ephemeral=True,
            )
            return

        if meal_name is None:
            view = TabetaiRemoveView(
                bot=bot,
                guild_id=guild_id,
                user_id=interaction.user.id,
                meal_options=options,
            )
            await interaction.response.send_message(
                embed=view.build_embed(),
                view=view,
                ephemeral=True,
            )
            view.message = await interaction.original_response()
            return

        requested_name = meal_name.strip()
        if not requested_name:
            await interaction.response.send_message(
                "meal_name cannot be empty.",
                ephemeral=True,
            )
            return

        target_name = ""
        for option in options:
            if option == requested_name:
                target_name = option
                break
        if not target_name:
            lowered = requested_name.lower()
            for option in options:
                if option.lower() == lowered:
                    target_name = option
                    break
        if not target_name:
            await interaction.response.send_message(
                f"找不到餐點：`{requested_name}`\n可改用 `/tabetai_remove` 不帶參數，用選單操作。",
                ephemeral=True,
            )
            return

        removed = await bot.db.remove_meal_option(guild_id, target_name)
        if not removed:
            await interaction.response.send_message(
                f"移除失敗：`{target_name}`",
                ephemeral=True,
            )
            return

        current_options = await bot.db.get_meal_options(guild_id)
        if current_options:
            await interaction.response.send_message(
                f"已移除餐點：`{target_name}`\n目前清單共 {len(current_options)} 項。",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "目前清單已清空，下一次 `/tabetai` 會自動載入完整預設清單。",
            ephemeral=True,
        )

    return tabetai_remove


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


def build_channel_activity_top_command(bot: HotmapBot) -> app_commands.Command:
    async def collect_forum_thread_ids(forum: discord.ForumChannel) -> List[int]:
        thread_ids: Set[int] = set()

        for thread in forum.threads:
            thread_ids.add(thread.id)

        try:
            active_threads = await forum.guild.active_threads()
            for thread in active_threads:
                if thread.parent_id == forum.id:
                    thread_ids.add(thread.id)
        except discord.HTTPException:
            pass

        try:
            async for thread in forum.archived_threads(limit=200):
                thread_ids.add(thread.id)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        return sorted(thread_ids)

    @app_commands.command(
        name="channel_top",
        description="Show channel/thread/forum active user ranking (top 10, max 180 days).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(
        channel="Target channel/thread/forum",
        days="Range in days (max 180)",
    )
    async def channel_top(
        interaction: discord.Interaction,
        channel: discord.TextChannel | discord.Thread | discord.ForumChannel,
        days: app_commands.Range[int, 1, 180] | None = None,
    ) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need server administrator permission to use this command.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        guild_id = interaction.guild_id
        if guild is None or guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        days_value = days or bot.settings.default_days
        days_value = min(days_value, bot.settings.max_days)
        from_time = datetime.now(timezone.utc) - timedelta(days=days_value)

        context_label = channel.mention
        if isinstance(channel, discord.ForumChannel):
            thread_ids = await collect_forum_thread_ids(channel)
            if not thread_ids:
                await interaction.followup.send(
                    f"No threads found under {channel.mention} for last {days_value} day(s)."
                )
                return
            rows = await bot.db.get_channel_user_activity_ranking_by_channel_ids(
                guild_id=guild_id,
                channel_ids=thread_ids,
                from_time=from_time,
                limit=10,
            )
            context_label = f"{channel.mention} (forum aggregate)"
        else:
            rows = await bot.db.get_channel_user_activity_ranking(
                guild_id=guild_id,
                channel_id=channel.id,
                from_time=from_time,
                limit=10,
            )
        if not rows:
            await interaction.followup.send(
                f"No active users found in {context_label} for last {days_value} day(s)."
            )
            return

        lines = [
            f"Here is {context_label} in last {days_value} day(s) active user ranking (top {len(rows)}).",
        ]
        for index, (author_id, author_display_name, count) in enumerate(rows, start=1):
            member_obj = guild.get_member(author_id)
            if member_obj is None:
                try:
                    member_obj = await guild.fetch_member(author_id)
                except discord.HTTPException:
                    member_obj = None
            if member_obj is not None:
                display_text = f"<@{author_id}>"
            else:
                display_name = author_display_name or "unknown-user"
                display_text = f"@{display_name}"
            lines.append(f"{index}. {display_text} - {format_count(count)}")

        await interaction.followup.send(
            "\n".join(lines),
            allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False),
        )

    return channel_top


def build_channels_top_user_command(bot: HotmapBot) -> app_commands.Command:
    @app_commands.command(
        name="channels_top_user",
        description="Show top active user per channel/thread/forum (max 180 days).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(days="Range in days (max 180)")
    async def channels_top_user(
        interaction: discord.Interaction,
        days: app_commands.Range[int, 1, 180] | None = None,
    ) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need server administrator permission to use this command.",
                ephemeral=True,
            )
            return

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        days_value = days or bot.settings.default_days
        days_value = min(days_value, bot.settings.max_days)
        from_time = datetime.now(timezone.utc) - timedelta(days=days_value)

        rows = await bot.db.get_channels_top_active_users(
            guild_id=guild_id,
            from_time=from_time,
        )
        if not rows:
            await interaction.followup.send(
                f"No active channels found in last {days_value} day(s)."
            )
            return

        guild = interaction.guild
        forum_author_counts: Dict[int, Dict[int, int]] = {}
        forum_name_by_id: Dict[int, str] = {}
        existing_channel_ids = {channel_id for channel_id, _, _, _ in rows}
        if guild is not None:
            for channel_id, _channel_name, author_id, count in rows:
                channel_obj = guild.get_channel(channel_id)
                if channel_obj is None:
                    channel_obj = guild.get_thread(channel_id)
                if not isinstance(channel_obj, discord.Thread):
                    continue
                parent = channel_obj.parent
                if not isinstance(parent, discord.ForumChannel):
                    continue
                forum_id = parent.id
                forum_name_by_id[forum_id] = parent.name
                bucket = forum_author_counts.setdefault(forum_id, {})
                bucket[author_id] = bucket.get(author_id, 0) + count

        forum_rows: List[Tuple[int, str, int, int]] = []
        for forum_id, author_counts in forum_author_counts.items():
            if forum_id in existing_channel_ids:
                continue
            top_author, top_count = sorted(author_counts.items(), key=lambda item: (-item[1], item[0]))[0]
            forum_name = forum_name_by_id.get(forum_id, f"forum-{forum_id}")
            forum_rows.append((forum_id, f"[Forum] {forum_name}", top_author, top_count))

        merged_rows = list(rows) + forum_rows
        merged_rows.sort(key=lambda item: (-item[3], item[0]))

        min_messages = max(1, days_value // CHANNEL_TOP_USER_MIN_DIVISOR)
        filtered_rows = [item for item in merged_rows if item[3] >= min_messages]
        if not filtered_rows:
            await interaction.followup.send(
                f"No channels reached threshold >= {min_messages} messages in last {days_value} day(s)."
            )
            return

        if len(filtered_rows) <= CHANNEL_TOP_USER_PAGE_SIZE:
            single_page_view = ChannelsTopUserPaginationView(
                guild=interaction.guild,
                invoker_user_id=interaction.user.id,
                days=days_value,
                min_messages=min_messages,
                rows=filtered_rows,
            )
            await interaction.followup.send(
                single_page_view.build_page_text(),
                allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False),
            )
            return

        pager_view = ChannelsTopUserPaginationView(
            guild=interaction.guild,
            invoker_user_id=interaction.user.id,
            days=days_value,
            min_messages=min_messages,
            rows=filtered_rows,
        )
        pager_view._sync_buttons()
        sent_message = await interaction.followup.send(
            pager_view.build_page_text(),
            view=pager_view,
            allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False),
            wait=True,
        )
        pager_view.message = sent_message

    return channels_top_user


def build_message_type_chart_command(bot: HotmapBot) -> app_commands.Command:
    def format_user_label(interaction: discord.Interaction, user: discord.User) -> str:
        guild = interaction.guild
        if guild is not None:
            target_member = guild.get_member(user.id)
            if target_member is not None:
                return f"@{target_member.display_name}"
        return f"@{user.global_name or user.name}"

    @app_commands.command(
        name="msgtype",
        description="Show message type pie chart (max 180 days).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(user="Target user", days="Range in days (max 180)")
    async def msgtype(
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

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.followup.send(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        days_value = days or bot.settings.default_days
        days_value = min(days_value, bot.settings.max_days)
        from_time = datetime.now(timezone.utc) - timedelta(days=days_value)
        rows = await bot.db.get_message_type_rows(
            guild_id=guild_id,
            author_id=user.id,
            from_time=from_time,
        )

        type_counts = {key: 0 for key in MESSAGE_TYPE_ORDER}
        other_reason_counts: Dict[str, int] = {}
        for content, attachments_json, stickers_json in rows:
            category = classify_message_type(content, attachments_json, stickers_json)
            type_counts[category] = type_counts.get(category, 0) + 1
            if category == MESSAGE_TYPE_OTHER:
                reason = classify_other_reason(content, attachments_json, stickers_json)
                other_reason_counts[reason] = other_reason_counts.get(reason, 0) + 1

        total_messages = len(rows)
        target_label = format_user_label(interaction, user)
        chart_text = render_message_type_text(
            user_label=target_label,
            days=days_value,
            type_counts=type_counts,
            total_messages=total_messages,
            other_reason_counts=other_reason_counts,
        )
        chart = render_message_type_pie_chart(
            user_label=target_label,
            days=days_value,
            type_counts=type_counts,
            total_messages=total_messages,
        )
        file = discord.File(chart, filename="message_type_chart.png")

        print(
            "[MsgType] "
            f"guild={guild_id}, author={user.id}, days={days_value}, "
            f"total_messages={total_messages}, counts={type_counts}, other_breakdown={other_reason_counts}"
        )

        await interaction.followup.send(f"```text\n{chart_text}\n```", file=file)

    return msgtype


def build_message_type_debug_command(bot: HotmapBot) -> app_commands.Command:
    def format_user_label(interaction: discord.Interaction, user: discord.User) -> str:
        guild = interaction.guild
        if guild is not None:
            target_member = guild.get_member(user.id)
            if target_member is not None:
                return f"@{target_member.display_name}"
        return f"@{user.global_name or user.name}"

    @app_commands.command(
        name="msgtype_debug",
        description="Debug message snapshot quality for message type analysis.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(user="Target user", days="Range in days (max 180)")
    async def msgtype_debug(
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

        await interaction.response.defer(thinking=True, ephemeral=True)

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.followup.send(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        days_value = days or bot.settings.default_days
        days_value = min(days_value, bot.settings.max_days)
        from_time = datetime.now(timezone.utc) - timedelta(days=days_value)
        rows = await bot.db.get_message_type_debug_rows(
            guild_id=guild_id,
            author_id=user.id,
            from_time=from_time,
        )

        type_counts = {key: 0 for key in MESSAGE_TYPE_ORDER}
        other_reason_counts: Dict[str, int] = {}
        pending_channel_counts: Dict[Tuple[int, str], int] = {}
        first_problem_time: datetime | None = None
        last_problem_time: datetime | None = None
        sample_message_ids: List[int] = []
        sample_messages: List[Tuple[int, int, str]] = []

        for message_id, channel_id, channel_name, created_at, content, attachments_json, stickers_json in rows:
            category = classify_message_type(content, attachments_json, stickers_json)
            type_counts[category] = type_counts.get(category, 0) + 1

            if category != MESSAGE_TYPE_OTHER:
                continue

            reason = classify_other_reason(content, attachments_json, stickers_json)
            other_reason_counts[reason] = other_reason_counts.get(reason, 0) + 1

            if reason != OTHER_REASON_EMPTY_PENDING:
                continue

            key = (channel_id, channel_name)
            pending_channel_counts[key] = pending_channel_counts.get(key, 0) + 1

            if isinstance(created_at, datetime):
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if first_problem_time is None or created_at < first_problem_time:
                    first_problem_time = created_at
                if last_problem_time is None or created_at > last_problem_time:
                    last_problem_time = created_at

            if len(sample_message_ids) < 10:
                sample_message_ids.append(message_id)
                sample_messages.append((message_id, channel_id, channel_name))

        problematic_channels = sorted(
            [(cid, cname, cnt) for (cid, cname), cnt in pending_channel_counts.items()],
            key=lambda x: x[2],
            reverse=True,
        )

        access_check_counts: Dict[str, int] = {}
        access_check_details: List[str] = []
        status_by_message_id: Dict[int, str] = {}
        guild = interaction.guild
        if guild is not None and sample_messages:
            access_check_counts, access_check_details, status_by_message_id = await check_message_access_samples(
                bot=bot,
                guild=guild,
                samples=sample_messages,
            )

        resolved_reason_counts = dict(other_reason_counts)
        pending_count = resolved_reason_counts.get(OTHER_REASON_EMPTY_PENDING, 0)
        checked_count = len(status_by_message_id)
        if pending_count > 0 and checked_count > 0:
            accessible_checked = sum(1 for status in status_by_message_id.values() if status == "可存取")
            inaccessible_checked = checked_count - accessible_checked
            remaining_pending = max(0, pending_count - checked_count)
            if remaining_pending > 0:
                resolved_reason_counts[OTHER_REASON_EMPTY_PENDING] = remaining_pending
            else:
                resolved_reason_counts.pop(OTHER_REASON_EMPTY_PENDING, None)

            if accessible_checked > 0:
                resolved_reason_counts[OTHER_REASON_ACCESSIBLE_EMPTY] = (
                    resolved_reason_counts.get(OTHER_REASON_ACCESSIBLE_EMPTY, 0) + accessible_checked
                )
            if inaccessible_checked > 0:
                resolved_reason_counts[OTHER_REASON_INACCESSIBLE] = (
                    resolved_reason_counts.get(OTHER_REASON_INACCESSIBLE, 0) + inaccessible_checked
                )

        debug_text = render_message_type_debug_text(
            user_label=format_user_label(interaction, user),
            days=days_value,
            total_messages=len(rows),
            type_counts=type_counts,
            other_reason_counts=resolved_reason_counts,
            problematic_channels=problematic_channels,
            first_problem_time=first_problem_time,
            last_problem_time=last_problem_time,
            sample_message_ids=sample_message_ids,
            access_check_counts=access_check_counts,
            access_check_details=access_check_details,
        )

        print(
            "[MsgTypeDebug] "
            f"guild={guild_id}, author={user.id}, days={days_value}, "
            f"total_messages={len(rows)}, other_breakdown={resolved_reason_counts}, "
            f"problem_channels={problematic_channels[:5]}"
        )
        await interaction.followup.send(f"```text\n{debug_text}\n```", ephemeral=True)

    return msgtype_debug


def build_message_inspect_command(bot: HotmapBot) -> app_commands.Command:
    @app_commands.command(
        name="msginspect",
        description="Inspect one message by message_id from Discord and DB snapshot.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(message_id="Target message ID")
    async def msginspect(
        interaction: discord.Interaction,
        message_id: str,
    ) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need server administrator permission to use this command.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        message_id_str = message_id.strip()
        if not message_id_str.isdigit():
            await interaction.followup.send(
                "message_id must be a numeric Discord snowflake.",
                ephemeral=True,
            )
            return
        message_id_int = int(message_id_str)

        db_row = await bot.db.get_message_snapshot(message_id_int)
        if db_row is None:
            await interaction.followup.send(
                f"message_id `{message_id_int}` not found in DB snapshot.",
                ephemeral=True,
            )
            return

        snapshot = bot._build_snapshot_from_db_row(db_row)
        channel_id = int(snapshot.get("channel_id", 0))
        channel_obj: discord.abc.GuildChannel | discord.Thread | None = guild.get_channel(channel_id)
        if channel_obj is None:
            channel_obj = guild.get_thread(channel_id)
        if channel_obj is None:
            try:
                fetched = await bot.fetch_channel(channel_id)
                if isinstance(fetched, (discord.TextChannel, discord.Thread)):
                    channel_obj = fetched
            except discord.HTTPException:
                channel_obj = None

        live_status = "未知"
        live_details: List[str] = []
        if not isinstance(channel_obj, (discord.TextChannel, discord.Thread)):
            live_status = "頻道不可用或無法讀取"
        else:
            try:
                live_msg = await channel_obj.fetch_message(message_id_int)
                live_status = "可存取"
                live_type = to_text(getattr(live_msg.type, "name", live_msg.type))
                live_details.append(f"- type: {live_type}")
                live_details.append(f"- is_system: {live_msg.is_system()}")
                live_details.append(f"- content: {repr(live_msg.content)}")
                live_details.append(f"- attachments: {len(live_msg.attachments)}")
                live_details.append(f"- stickers: {len(live_msg.stickers)}")
                live_details.append(f"- jump_url: {live_msg.jump_url}")
            except discord.NotFound:
                live_status = "已刪除或不存在"
            except discord.Forbidden:
                live_status = "權限不足"
            except discord.HTTPException as exc:
                live_status = f"讀取失敗: {exc}"

        db_content = to_text(snapshot.get("content"))
        db_attachments = snapshot.get("attachments", [])
        db_stickers = snapshot.get("stickers", [])
        db_reason = classify_other_reason(
            db_content,
            json.dumps(db_attachments, ensure_ascii=False),
            json.dumps(db_stickers, ensure_ascii=False),
        )

        lines = [
            f"message_id: {message_id_int}",
            f"channel: <#{channel_id}> ({to_text(snapshot.get('channel_name'))})",
            f"Discord即時狀態: {live_status}",
            "",
            "DB快照:",
            f"- created_at: {snapshot.get('created_at')}",
            f"- author_id: {snapshot.get('author_id')}",
            f"- content: {repr(db_content)}",
            f"- attachments: {len(db_attachments)}",
            f"- stickers: {len(db_stickers)}",
            f"- custom_emojis: {len(snapshot.get('custom_emojis', []))}",
            f"- reference_message_id: {snapshot.get('reference_message_id')}",
            f"- reference_author_id: {snapshot.get('reference_author_id')}",
            f"- reply_mention_enabled: {snapshot.get('reply_mention_enabled')}",
            f"- mentions_users: {len(snapshot.get('mentions_users', []))}",
            f"- mentions_roles: {len(snapshot.get('mentions_roles', []))}",
            f"- mentions_everyone: {snapshot.get('mentions_everyone')}",
            f"- 分類推論: {db_reason}",
        ]

        if live_details:
            lines.append("")
            lines.append("Discord即時內容:")
            lines.extend(live_details)

        await interaction.followup.send(f"```text\n{chr(10).join(lines)}\n```", ephemeral=True)

    return msginspect


def build_set_delete_log_command(bot: HotmapBot) -> app_commands.Command:
    @app_commands.command(
        name="set_delete_log",
        description="Set a channel to receive deleted message logs.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(channel="Target channel for deleted message logs")
    async def set_delete_log(
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need server administrator permission to use this command.",
                ephemeral=True,
            )
            return

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        if guild is None or guild.me is None:
            await interaction.response.send_message(
                "Bot member state is not ready yet. Please try again later.",
                ephemeral=True,
            )
            return

        perms = channel.permissions_for(guild.me)
        missing = []
        if not perms.view_channel:
            missing.append("View Channel")
        if not perms.send_messages:
            missing.append("Send Messages")
        if not perms.embed_links:
            missing.append("Embed Links")
        if missing:
            await interaction.response.send_message(
                "Bot is missing permissions in target channel: " + ", ".join(missing),
                ephemeral=True,
            )
            return

        await bot.db.set_delete_log_channel(guild_id, channel.id)
        await interaction.response.send_message(
            f"Deleted message logs will be sent to {channel.mention}.",
            ephemeral=True,
        )

    return set_delete_log


def build_delete_log_status_command(bot: HotmapBot) -> app_commands.Command:
    @app_commands.command(
        name="delete_log_status",
        description="Show deleted message log configuration and bot permissions.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def delete_log_status(interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need server administrator permission to use this command.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        guild_id = interaction.guild_id
        if guild is None or guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        delete_log_channel_id = await bot.db.get_delete_log_channel(guild_id)
        if delete_log_channel_id is None:
            await interaction.response.send_message(
                "Delete log channel is not set. Use /set_delete_log first.",
                ephemeral=True,
            )
            return

        channel_obj = bot.get_channel(delete_log_channel_id)
        if channel_obj is None:
            try:
                channel_obj = await bot.fetch_channel(delete_log_channel_id)
            except discord.HTTPException:
                channel_obj = None

        if not isinstance(channel_obj, discord.TextChannel):
            await interaction.response.send_message(
                f"Configured channel `{delete_log_channel_id}` is unavailable or not a text channel.",
                ephemeral=True,
            )
            return

        if guild.me is None:
            await interaction.response.send_message(
                "Bot member state is not ready yet. Please try again later.",
                ephemeral=True,
            )
            return

        perms = channel_obj.permissions_for(guild.me)
        missing = []
        if not perms.view_channel:
            missing.append("View Channel")
        if not perms.send_messages:
            missing.append("Send Messages")
        if not perms.embed_links:
            missing.append("Embed Links")

        if missing:
            await interaction.response.send_message(
                "Delete log channel: "
                f"{channel_obj.mention}\n"
                "Bot missing permissions: "
                + ", ".join(missing),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Delete log is configured correctly.\n"
            f"Channel: {channel_obj.mention} (`{channel_obj.id}`)\n"
            "Permissions: View Channel, Send Messages, Embed Links",
            ephemeral=True,
        )

    return delete_log_status


async def run() -> None:
    load_dotenv()
    settings = Settings.load()
    print(
        "[Settings] "
        f"default_days={settings.default_days}, max_days={settings.max_days}, "
        f"history_backfill_on_startup={settings.history_backfill_on_startup}, "
        f"history_backfill_days={settings.history_backfill_days}, "
        f"cleanup_on_startup={settings.cleanup_on_startup}, "
        f"cleanup_days={settings.cleanup_days}"
    )
    db = Database(settings.database_url)
    await db.connect()

    bot = HotmapBot(settings, db)
    bot.tree.add_command(build_tabetai_command(bot))
    bot.tree.add_command(build_tabetai_clear_command(bot))
    bot.tree.add_command(build_tabetai_add_command(bot))
    bot.tree.add_command(build_tabetai_remove_command(bot))
    bot.tree.add_command(build_hotmap_command(bot))
    bot.tree.add_command(build_channel_activity_top_command(bot))
    bot.tree.add_command(build_channels_top_user_command(bot))
    bot.tree.add_command(build_message_type_chart_command(bot))
    bot.tree.add_command(build_message_type_debug_command(bot))
    bot.tree.add_command(build_message_inspect_command(bot))
    bot.tree.add_command(build_set_delete_log_command(bot))
    bot.tree.add_command(build_delete_log_status_command(bot))

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
