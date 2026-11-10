"""Record which clients can use the schema of a PostgreSQL database."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from alembic.runtime.migration import MigrationContext, MigrationInfo
from alembic.script import ScriptDirectory
from packaging.version import Version
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, update

from lightly_studio.errors import SchemaCompatError
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


def check_client_compatibility(
    row: SchemaCompatTable | None,
    client_version: str,
    script: ScriptDirectory,
) -> None:
    """Check that a client that does not migrate can use the database.

    Args:
        row: The ``schema_compat`` row of the database, or None when it has none.
        client_version: The lightly-studio version of this client.
        script: The Alembic script directory of this client.

    Raises:
        SchemaCompatError: If the database has no row, needs a newer client, or is behind
            the schema that this client knows.
    """
    if row is None:
        raise SchemaCompatError(
            "The database has no schema compatibility row. Upgrade the server first."
        )
    if Version(client_version) < Version(row.min_client_version):
        raise SchemaCompatError(
            f"The database needs lightly-studio >= {row.min_client_version}, "
            f"this client is {client_version}."
        )
    head = script.get_current_head()
    if row.oss_revision == head:
        return
    ancestors = {rev.revision for rev in script.iterate_revisions(upper=head, lower="base")}
    if row.oss_revision in ancestors:
        raise SchemaCompatError(
            f"The database schema is at revision {row.oss_revision}, this client expects "
            f"{head}. Upgrade the server first."
        )
    # Unknown revision: the database has newer, additive migrations. The client continues.
