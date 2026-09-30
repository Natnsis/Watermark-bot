import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TIMEZONE = ZoneInfo("Africa/Addis_Ababa")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    db_require_ssl: bool


def _normalize_db_url(url: str) -> tuple[str, bool]:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    require_ssl = query.pop("sslmode", "") == "require" or (parts.hostname or "").endswith("neon.tech")
    query.pop("channel_binding", None)
    normalized = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return normalized, require_ssl


@lru_cache
def get_settings() -> Settings:
    database_url, db_require_ssl = _normalize_db_url(os.environ["DATABASE_URL"])
    return Settings(
        bot_token=os.environ["BOT_TOKEN"],
        database_url=database_url,
        db_require_ssl=db_require_ssl,
    )
