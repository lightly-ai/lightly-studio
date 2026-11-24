"""PostgreSQL schema migrations via Alembic.

Empty and tracked DBs run ``upgrade head``; legacy DBs (tables, no
``alembic_version``) are stamped to head without applying revisions.

A package that extends lightly_studio can pass its own migrations. They have their own
linear history and version table, and run in the order in which they were written.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import Script, ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.engine import Engine, Inspector

import lightly_studio.api.db_tables  # noqa: F401
from lightly_studio.database import db_url
from lightly_studio.migrations.config_utils import ensure_script_location, find_alembic_ini


@dataclass(frozen=True)
class ExtensionMigrations:
    """The Alembic migrations of a package that extends lightly_studio.

    The extension has its own linear history and its own version table. Each revision of
    the extension sets the module attribute ``oss_revision`` to the lightly_studio
    revision that it was written against.

    Attributes:
        script_location: Directory with the ``env.py`` and the ``versions`` directory of
            the extension.
        version_table_schema: Schema of the version table of the extension. The ``env.py``
            of the extension uses the same schema.
        version_table: Name of the version table of the extension. The ``env.py`` of the
            extension uses the same name.
    """

    script_location: Path
    version_table_schema: str
    version_table: str = "alembic_version"


class _ExtensionRevision(NamedTuple):
    revision: str
    oss_revision: str


def run_migrations(
    engine: Engine,
    engine_url: str,
    extension_migrations: ExtensionMigrations | None = None,
) -> None:
    """Apply Alembic migrations for the connected Postgres database.

    With extension migrations, the revisions of both histories run in the order in which
    they were written. For each pending extension revision, lightly_studio is first
    upgraded to the ``oss_revision`` of that revision. Last, lightly_studio is upgraded to
    its head. A new and an existing database then apply the same sequence.

    Args:
        engine: SQLAlchemy engine bound to the target Postgres database.
        engine_url: Database URL (used for Alembic config).
        extension_migrations: The migrations of a package that extends lightly_studio.

    Raises:
        RuntimeError: If the extension history is not linear, an extension revision does
            not set a known ``oss_revision``, or the database has an extension revision
            that the extension does not have.
    """
    config = get_alembic_config(engine_url=engine_url)

    if _alembic_version_table_exists(engine=engine):
        logging.info("Applying pending Alembic migrations (upgrade head).")
    else:
        logging.info("Initializing empty PostgreSQL database (upgrade head).")

    if extension_migrations is not None:
        _upgrade_extension(
            engine=engine,
            engine_url=engine_url,
            config=config,
            extension_migrations=extension_migrations,
        )

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
    # db_migrations.py lives in the `database` subpackage, so go up one level to
    # reach the package root where alembic.ini and the migrations package live.
    package_dir = Path(__file__).resolve().parent.parent
    alembic_config = Config(str(find_alembic_ini(package_dir=package_dir)))
    migrations_dir = package_dir / "migrations"
    ensure_script_location(config=alembic_config, migrations_dir=migrations_dir)
    return alembic_config


def _upgrade_extension(
    engine: Engine,
    engine_url: str,
    config: Config,
    extension_migrations: ExtensionMigrations,
) -> None:
    """Apply each pending extension revision after the revision it was written against."""
    extension_config = Config()
    extension_config.set_main_option(
        name="script_location", value=str(extension_migrations.script_location)
    )
    extension_config.set_main_option(
        name="sqlalchemy.url", value=db_url.ensure_psycopg3_driver(engine_url=engine_url)
    )
    revisions = _get_extension_revisions(
        oss_script=ScriptDirectory.from_config(config=config),
        extension_script=ScriptDirectory.from_config(config=extension_config),
    )
    applied = _get_applied_extension_revision(
        engine=engine, extension_migrations=extension_migrations
    )
    for revision in _get_pending_revisions(revisions=revisions, applied=applied):
        logging.info(
            f"Applying extension revision {revision.revision} "
            f"after revision {revision.oss_revision}."
        )
        _run_alembic_command(
            engine=engine, config=config, fn=command.upgrade, revision=revision.oss_revision
        )
        _run_alembic_command(
            engine=engine, config=extension_config, fn=command.upgrade, revision=revision.revision
        )


def _get_extension_revisions(
    oss_script: ScriptDirectory, extension_script: ScriptDirectory
) -> list[_ExtensionRevision]:
    """Return the extension revisions with their ``oss_revision``, oldest first."""
    scripts = list(extension_script.walk_revisions())
    _ensure_linear_history(scripts=scripts, heads=extension_script.get_heads())
    oss_revisions = {script.revision for script in oss_script.walk_revisions()}
    revisions = []
    # walk_revisions goes from the head to the base.
    for script in reversed(scripts):
        oss_revision = getattr(script.module, "oss_revision", None)
        if oss_revision is None:
            raise RuntimeError(f"Extension revision {script.revision} does not set oss_revision.")
        if oss_revision not in oss_revisions:
            raise RuntimeError(
                f"Extension revision {script.revision} sets oss_revision to {oss_revision!r}, "
                "which is not a lightly_studio revision."
            )
        revisions.append(_ExtensionRevision(revision=script.revision, oss_revision=oss_revision))
    return revisions


def _ensure_linear_history(scripts: Sequence[Script], heads: Sequence[str]) -> None:
    """Raise if the history has more than one head, a branch point, or a merge point.

    A merged history has one head, but the order of its parallel revisions is not defined.
    """
    branch_or_merge_points = [
        script.revision for script in scripts if script.is_branch_point or script.is_merge_point
    ]
    if len(heads) > 1 or branch_or_merge_points:
        raise RuntimeError(
            f"The extension migrations must be linear. Heads: {list(heads)}, "
            f"branch or merge points: {branch_or_merge_points}."
        )


def _get_applied_extension_revision(
    engine: Engine, extension_migrations: ExtensionMigrations
) -> str | None:
    """Return the extension revision in the version table of the extension."""
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection=connection,
            opts={
                "version_table": extension_migrations.version_table,
                "version_table_schema": extension_migrations.version_table_schema,
            },
        )
        return context.get_current_revision()


def _get_pending_revisions(
    revisions: Sequence[_ExtensionRevision], applied: str | None
) -> Sequence[_ExtensionRevision]:
    """Return the revisions after the applied one."""
    if applied is None:
        return revisions
    revision_ids = [revision.revision for revision in revisions]
    if applied not in revision_ids:
        raise RuntimeError(
            f"The database has extension revision {applied}, which the extension does not have."
        )
    return revisions[revision_ids.index(applied) + 1 :]


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
