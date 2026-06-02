import os
from dataclasses import dataclass


def _require_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def _parse_bool(value: str, default: bool = False) -> bool:
    text = value.strip().lower()
    if not text:
        return default
    return text in ("1", "true", "yes", "y", "on")


@dataclass(frozen=True)
class Settings:
    discord_token: str
    database_url: str
    default_days: int
    max_days: int
    ingest_log_interval_sec: int
    history_backfill_on_startup: bool
    history_backfill_days: int
    cleanup_on_startup: bool
    cleanup_days: int

    @staticmethod
    def load() -> "Settings":
        default_days = int(os.getenv("HOTMAP_DEFAULT_DAYS", "30"))
        max_days = int(os.getenv("HOTMAP_MAX_DAYS", "30"))
        ingest_log_interval_sec = int(os.getenv("HOTMAP_INGEST_LOG_INTERVAL_SEC", "60"))
        history_backfill_on_startup = _parse_bool(os.getenv("HOTMAP_HISTORY_BACKFILL_ON_STARTUP", "true"), True)
        history_backfill_days = int(os.getenv("HOTMAP_HISTORY_BACKFILL_DAYS", "30"))
        cleanup_on_startup = _parse_bool(os.getenv("HOTMAP_CLEANUP_ON_STARTUP", "false"), False)
        cleanup_days = int(os.getenv("HOTMAP_CLEANUP_DAYS", "30"))
        if max_days > 180:
            max_days = 180
        if ingest_log_interval_sec < 5:
            ingest_log_interval_sec = 5
        if history_backfill_days < 1:
            history_backfill_days = 1
        if history_backfill_days > 180:
            history_backfill_days = 180
        if cleanup_days < 1:
            cleanup_days = 1
        if cleanup_days > 180:
            cleanup_days = 180

        return Settings(
            discord_token=_require_env("DISCORD_TOKEN"),
            database_url=_require_env("DATABASE_URL"),
            default_days=default_days,
            max_days=max_days,
            ingest_log_interval_sec=ingest_log_interval_sec,
            history_backfill_on_startup=history_backfill_on_startup,
            history_backfill_days=history_backfill_days,
            cleanup_on_startup=cleanup_on_startup,
            cleanup_days=cleanup_days,
        )
