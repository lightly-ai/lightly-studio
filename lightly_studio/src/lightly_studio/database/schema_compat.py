"""Record which clients can use the schema of a PostgreSQL database."""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session

from lightly_studio.models.schema_compat import SchemaCompatTable

# The lowest lightly-studio version that can use the current schema. A breaking
# migration raises this constant in the same pull request.
MIN_SUPPORTED_CLIENT_VERSION = "1.2.1"


def write_schema_compat(engine: Engine, oss_revision: str) -> None:
    """Write the single ``schema_compat`` row after a schema upgrade.

    Args:
        engine: Engine bound to the upgraded database.
        oss_revision: The Alembic revision that the upgrade applied.
    """
    with Session(engine) as session:
        row = session.get(SchemaCompatTable, 1)
        if row is None:
            row = SchemaCompatTable(
                oss_revision=oss_revision,
                min_client_version=MIN_SUPPORTED_CLIENT_VERSION,
            )
        else:
            row.oss_revision = oss_revision
            row.min_client_version = MIN_SUPPORTED_CLIENT_VERSION
        session.add(row)
        session.commit()


def read_schema_compat(engine: Engine) -> SchemaCompatTable | None:
    """Return the ``schema_compat`` row, or None when the database has none.

    Args:
        engine: Engine bound to the database.
    """
    with Session(engine) as session:
        return session.get(SchemaCompatTable, 1)
