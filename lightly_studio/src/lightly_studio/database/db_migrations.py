"""PostgreSQL schema migrations via Alembic.

The revisions in this package form the ``oss`` branch. Extra version locations add
branches whose first revision depends on the ``oss`` head. Without extra locations the
upgrade target is ``oss@head``, with them it is ``heads``.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.engine import Engine, Inspector

import lightly_studio.api.db_tables  # noqa: F401
from lightly_studio.database import db_url
from lightly_studio.migrations.config_utils import ensure_script_location, find_alembic_ini

OSS_HEAD = "oss@head"


def run_migrations(
    engine: Engine,
    engine_url: str,
    extra_version_locations: Sequence[str] = (),
) -> None:
    """Apply Alembic migrations for the connected Postgres database.

    Args:
        engine: SQLAlchemy engine bound to the target Postgres database.
        engine_url: Database URL (used for Alembic config).
        extra_version_locations: Directories with revisions of other branches.
    """
    config = get_alembic_config(
        engine_url=engine_url, extra_version_locations=extra_version_locations
    )
    revision = "heads" if extra_version_locations else OSS_HEAD

    if _alembic_version_table_exists(engine=engine):
        logging.info(f"Applying pending Alembic migrations (upgrade {revision}).")
    else:
        logging.info(f"Initializing empty PostgreSQL database (upgrade {revision}).")

    _run_alembic_command(
        engine=engine,
        config=config,
        fn=command.upgrade,
        revision=revision,
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


def get_alembic_config(
    engine_url: str,
    extra_version_locations: Sequence[str] = (),
) -> Config:
    """Build an Alembic Config for the given Postgres URL.

    Args:
        engine_url: Postgres database URL.
        extra_version_locations: Directories with revisions of other branches.

    Returns:
        Alembic Config with sqlalchemy.url and script_location set.
    """
    alembic_config = _base_config(extra_version_locations=extra_version_locations)
    url = db_url.ensure_psycopg3_driver(engine_url=engine_url)
    alembic_config.set_main_option(name="sqlalchemy.url", value=url)
    return alembic_config


def _base_config(extra_version_locations: Sequence[str] = ()) -> Config:
    """Load alembic.ini and point it at the migrations package."""
    # db_migrations.py lives in the `database` subpackage, so go up one level to
    # reach the package root where alembic.ini and the migrations package live.
    package_dir = Path(__file__).resolve().parent.parent
    alembic_config = Config(str(find_alembic_ini(package_dir=package_dir)))
    migrations_dir = package_dir / "migrations"
    ensure_script_location(config=alembic_config, migrations_dir=migrations_dir)
    if extra_version_locations:
        _add_version_locations(
            config=alembic_config, extra_version_locations=extra_version_locations
        )
    return alembic_config


def _add_version_locations(config: Config, extra_version_locations: Sequence[str]) -> None:
    """Add extra version directories next to the ``versions`` directory of the package."""
    script_location = config.get_main_option(name="script_location")
    if script_location is None:
        raise RuntimeError("Alembic script_location is not set.")
    locations = [str(Path(script_location) / "versions"), *extra_version_locations]
    # Alembic 1.16+ reads path_separator, older versions read version_path_separator.
    config.set_main_option(name="path_separator", value="os")
    config.set_main_option(name="version_path_separator", value="os")
    config.set_main_option(name="version_locations", value=os.pathsep.join(locations))


def _run_alembic_command(
    engine: Engine,
    config: Config,
    fn: Callable[..., None],
    revision: str,
) -> None:
    """Run an Alembic command using the application engine connection.

    Shares the connection with env.py via Config.attributes.
    """
    # Alembic's env.py controls migration transaction boundaries.
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        fn(config, revision=revision)


def _get_inspector(engine: Engine) -> Inspector:
    """Return a schema inspector for the given engine."""
    return inspect(engine)


def _alembic_version_table_exists(engine: Engine) -> bool:
    """Return whether the Alembic version tracking table is present."""
    return bool(_get_inspector(engine=engine).has_table(table_name="alembic_version"))
