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


def run_migrations(engine: Engine, engine_url: str) -> None:
    """Apply Alembic migrations for the connected Postgres database.

    Args:
        engine: SQLAlchemy engine bound to the target Postgres database.
        engine_url: Database URL (used for Alembic config).
    """
    config = get_alembic_config(engine_url=engine_url)

    if _has_application_tables(engine=engine) and not _alembic_version_table_exists(
        engine=engine,
    ):
        logging.info("Adopting pre-Alembic database schema (stamp head).")
        logging.warning(
            "Database has application tables but no alembic_version row. "
            "Stamped head without running migrations; verify schema matches revision "
            "fa45898e4138 before relying on Alembic upgrades."
        )
        _run_alembic_command(
            engine=engine,
            config=config,
            fn=command.stamp,
            revision="head",
        )
        return

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
    alembic_config = Config(str(_find_alembic_ini()))
    _ensure_script_location(config=alembic_config)
    return alembic_config


def _find_alembic_ini() -> Path:
    """Return the path to alembic.ini for development or installed layouts."""
    package_dir = Path(__file__).resolve().parent
    installed_ini = package_dir / "alembic.ini"
    if installed_ini.is_file():
        return installed_ini

    dev_ini = package_dir.parent.parent / "alembic.ini"
    if dev_ini.is_file():
        return dev_ini

    raise FileNotFoundError("alembic.ini not found for Alembic migrations.")


def _ensure_script_location(config: Config) -> None:
    """Point Alembic at the migrations package (dev and wheel layouts differ in alembic.ini)."""
    script_location = config.get_main_option(name="script_location")
    if script_location is not None and Path(script_location).is_dir():
        return
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    config.set_main_option(name="script_location", value=str(migrations_dir))


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
