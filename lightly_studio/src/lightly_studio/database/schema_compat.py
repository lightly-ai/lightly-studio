"""Record which clients can use the schema of a PostgreSQL database."""

from __future__ import annotations

from sqlalchemy.engine import Connection, Engine
from sqlmodel import Session, delete, insert

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
