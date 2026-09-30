from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

# Additive migration for columns added to `users` after its first deploy.
# SQLAlchemy's create_all() only creates missing tables, never alters
# existing ones, so new User columns need to be added here by hand.
_USER_COLUMN_MIGRATIONS = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS channel_id BIGINT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS channel_title VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_next_number INTEGER",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_next_bracket INTEGER",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_stage VARCHAR(20)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_completion_draft TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_progress_draft TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS awaiting_project_log_id INTEGER",
)


def init_db(database_url: str, require_ssl: bool) -> None:
    global _engine, _session_factory
    connect_args = {"ssl": "require"} if require_ssl else {}
    _engine = create_async_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def create_tables() -> None:
    assert _engine is not None, "init_db must be called first"
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for statement in _USER_COLUMN_MIGRATIONS:
            await conn.execute(text(statement))


def get_session() -> AsyncSession:
    assert _session_factory is not None, "init_db must be called first"
    return _session_factory()


async def run_statements(statements: tuple[str, ...]) -> None:
    assert _engine is not None, "init_db must be called first"
    async with _engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))


async def create_table(model: type[Base]) -> None:
    assert _engine is not None, "init_db must be called first"
    async with _engine.begin() as conn:
        await conn.run_sync(model.__table__.create, checkfirst=True)
