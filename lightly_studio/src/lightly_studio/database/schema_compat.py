"""Record which clients can use the schema of a PostgreSQL database."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from alembic.runtime.migration import MigrationContext, MigrationInfo
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, update

from lightly_studio.models.schema_compat import SchemaCompatTable


def on_version_apply(
    ctx: MigrationContext,
    step: MigrationInfo,
    heads: Collection[str],
    *_alembic_args: Any,
    **_alembic_kwargs: Any,
) -> None:
    """Update the ``schema_compat`` row after each revision, in its transaction.

    Alembic calls this hook after it updates ``alembic_version`` for a revision. The
    row gets the new head as ``oss_revision``. A revision that breaks older clients
    declares the module attribute ``min_client_version``, and the upgrade writes it to
    the row. The row and the schema are then committed together, or not at all.

    In offline mode (``--sql``) and with more than one head, the hook does not update
    the row. A downgrade keeps ``min_client_version``.

    Args:
        ctx: The Alembic migration context.
        step: The revision that was applied.
        heads: The heads after the revision.
        _alembic_args: The other arguments of the Alembic hook, not used.
        _alembic_kwargs: The other arguments of the Alembic hook, not used.
    """
    connection = ctx.connection
    # The table does not exist before the revision that creates it, or after its downgrade.
    if (
        ctx.as_sql
        or connection is None
        or len(heads) != 1
        or not inspect(connection).has_table(table_name="schema_compat")
    ):
        return
    values = {"oss_revision": next(iter(heads))}
    module = getattr(step.up_revision, "module", None)
    min_client_version = getattr(module, "min_client_version", None)
    if step.is_upgrade and min_client_version is not None:
        values["min_client_version"] = min_client_version
    connection.execute(
        update(SchemaCompatTable).where(col(SchemaCompatTable.id) == 1).values(**values)
    )


def read_schema_compat(engine: Engine) -> SchemaCompatTable | None:
    """Return the ``schema_compat`` row, or None when the database has none.

    The database has no row when it has no ``schema_compat`` table yet.

    Args:
        engine: Engine bound to the database.
    """
    if not inspect(engine).has_table(table_name="schema_compat"):
        return None
    with Session(engine) as session:
        return session.get(SchemaCompatTable, 1)
