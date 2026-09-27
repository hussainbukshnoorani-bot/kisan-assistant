from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from kisan.config import database_url_from_env
from kisan.db.models import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    # Set by kisan.db.migrate.upgrade; otherwise DATABASE_URL from the environment or .env
    return config.get_main_option("sqlalchemy.url") or database_url_from_env()


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
