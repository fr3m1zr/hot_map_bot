import os
from dataclasses import dataclass


def _require_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


@dataclass(frozen=True)
class Settings:
    discord_token: str
    database_url: str
    default_days: int
    max_days: int
    ingest_log_interval_sec: int

    @staticmethod
    def load() -> "Settings":
        default_days = int(os.getenv("HOTMAP_DEFAULT_DAYS", "30"))
        max_days = int(os.getenv("HOTMAP_MAX_DAYS", "30"))
        ingest_log_interval_sec = int(os.getenv("HOTMAP_INGEST_LOG_INTERVAL_SEC", "60"))
        if max_days > 30:
            max_days = 30
        if ingest_log_interval_sec < 5:
            ingest_log_interval_sec = 5

        return Settings(
            discord_token=_require_env("DISCORD_TOKEN"),
            database_url=_require_env("DATABASE_URL"),
            default_days=default_days,
            max_days=max_days,
            ingest_log_interval_sec=ingest_log_interval_sec,
        )
