from sqlalchemy import create_engine, pool
from alembic import context

from src.db import DATABASE_URL, Base
from src.chores_planner import models  # noqa: F401

config = context.config

# Derive sync URL from the async one (strip async driver suffix, e.g. +aiosqlite)
SYNC_DATABASE_URL = DATABASE_URL.replace("+aiosqlite", "")
config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=SYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(SYNC_DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
