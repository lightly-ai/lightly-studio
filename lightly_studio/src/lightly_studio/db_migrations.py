"""PostgreSQL schema migrations via Alembic.

Empty and tracked DBs run ``upgrade head``; legacy DBs (tables, no
``alembic_version``) are stamped to head without applying revisions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.engine import Engine, Inspector
from sqlmodel import SQLModel

import lightly_studio.api.db_tables  # noqa: F401
from lightly_studio import db_url
from lightly_studio.migrations.config_utils import ensure_script_location, find_alembic_ini


def run_migrations(engine: Engine, engine_url: str) -> None:
    """Apply Alembic migrations for the connected Postgres database.

    Args:
        engine: SQLAlchemy engine bound to the target Postgres database.
        engine_url: Database URL (used for Alembic config).
    """
    config = get_alembic_config(engine_url=engine_url)

    if _alembic_version_table_exists(engine=engine):
        logging.info("Applying pending Alembic migrations (upgrade head).")
    else:
        logging.info("Initializing empty PostgreSQL database (upgrade head).")

    _run_alembic_command(
        engine=engine,
        config=config,
        fn=command.upgrade,
        revision="head",
    )


def get_head_revision() -> str:
    """Return the current Alembic head revision id.

    Returns:
        Head revision string.

    Raises:
        RuntimeError: If no head revision is defined in the migrations package.
    """
    script = ScriptDirectory.from_config(config=_base_config())
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("No Alembic head revision found in migrations/scripts.")
    return head


def get_alembic_config(engine_url: str) -> Config:
    """Build an Alembic Config for the given Postgres URL.

    Args:
        engine_url: Postgres database URL.

    Returns:
        Alembic Config with sqlalchemy.url and script_location set.
    """
    alembic_config = _base_config()
    url = db_url.ensure_psycopg3_driver(engine_url=engine_url)
    alembic_config.set_main_option(name="sqlalchemy.url", value=url)
    return alembic_config


def _base_config() -> Config:
    """Load alembic.ini and point it at the migrations package."""
    package_dir = Path(__file__).resolve().parent
    alembic_config = Config(str(find_alembic_ini(package_dir=package_dir)))
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    ensure_script_location(config=alembic_config, migrations_dir=migrations_dir)
    return alembic_config


def _run_alembic_command(
    engine: Engine,
    config: Config,
    fn: Callable[..., None],
    revision: str,
) -> None:
    """Run an Alembic command using the application engine connection.

    Shares the connection with env.py via Config.attributes.
    """
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        fn(config, revision=revision)


def _get_inspector(engine: Engine) -> Inspector:
    """Return a schema inspector for the given engine."""
    return inspect(engine)


def _alembic_version_table_exists(engine: Engine) -> bool:
    """Return whether the Alembic version tracking table is present."""
    return bool(_get_inspector(engine=engine).has_table(table_name="alembic_version"))


def _has_application_tables(engine: Engine) -> bool:
    """Return whether any SQLModel application table exists in the database."""
    existing_tables = set(_get_inspector(engine=engine).get_table_names())
    application_tables = set(SQLModel.metadata.tables.keys())
    return bool(existing_tables & application_tables)
