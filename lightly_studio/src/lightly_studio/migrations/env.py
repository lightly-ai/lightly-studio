"""Alembic migration environment for PostgreSQL schema management.

Executed on every Alembic CLI invocation (upgrade, revision --autogenerate, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path

from alembic import context
from sqlalchemy import engine, pool
from sqlmodel import SQLModel

# Register all SQLModel tables so autogenerate sees the full schema.
import lightly_studio.api.db_tables  # noqa: F401
from lightly_studio.dataset.env import LIGHTLY_STUDIO_DATABASE_URL

config = context.config


def _ensure_script_location() -> None:
    """Use the migrations package directory when the ini path is for source layouts."""
    script_location = config.get_main_option("script_location")
    if script_location is not None and Path(script_location).is_dir():
        return
    # Installed wheels place alembic.ini under lightly_studio/; the dev-only
    # src/lightly_studio/migrations path from alembic.ini does not exist there.
    config.set_main_option("script_location", str(Path(__file__).parent))


def _configure_database_url() -> None:
    """Set sqlalchemy.url on the Alembic config from LIGHTLY_STUDIO_DATABASE_URL."""
    if LIGHTLY_STUDIO_DATABASE_URL is None:
        raise RuntimeError("LIGHTLY_STUDIO_DATABASE_URL must be set for Alembic migrations.")

    url = LIGHTLY_STUDIO_DATABASE_URL
    # Match db_manager: use psycopg3, not SQLAlchemy's default psycopg2 driver.
    if url.startswith("postgres"):
        url = re.sub(r"^(postgresql|postgres)://", "postgresql+psycopg://", url)
    config.set_main_option("sqlalchemy.url", url)


_ensure_script_location()

# Schema autogenerate diffs this metadata against the live Postgres catalog.
target_metadata = SQLModel.metadata

_configure_database_url()

# NullPool: one connection per CLI run, not a long-lived pool.
connectable = engine.engine_from_config(
    config.get_section(config.config_ini_section, {}),
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
)

with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()
