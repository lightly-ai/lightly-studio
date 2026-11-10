"""Record which clients can use the schema of a PostgreSQL database."""

from __future__ import annotations

from alembic.script import ScriptDirectory
from packaging.version import Version
from sqlalchemy.engine import Connection, Engine
from sqlmodel import Session, delete, insert

from lightly_studio.errors import SchemaCompatError
from lightly_studio.models.schema_compat import SchemaCompatTable

# The lowest lightly-studio version that can use the current schema. A breaking
# migration raises this constant in the same pull request.
MIN_SUPPORTED_CLIENT_VERSION = "1.2.1"


def write_schema_compat(connection: Connection, oss_revision: str) -> None:
    """Write the single ``schema_compat`` row in the transaction of a schema upgrade.

    The caller commits. The row and the schema upgrade are then one transaction.

    Args:
        connection: The connection that runs the schema upgrade.
        oss_revision: The Alembic revision that the upgrade applied.
    """
    connection.execute(delete(SchemaCompatTable))
    connection.execute(
        insert(SchemaCompatTable).values(
            id=1,
            oss_revision=oss_revision,
            min_client_version=MIN_SUPPORTED_CLIENT_VERSION,
        )
    )


def read_schema_compat(engine: Engine) -> SchemaCompatTable | None:
    """Return the ``schema_compat`` row, or None when the database has none.

    Args:
        engine: Engine bound to the database.
    """
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
