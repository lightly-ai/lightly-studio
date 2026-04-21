"""Validation of LightlyStudio database version metadata."""

from __future__ import annotations

import logging
from importlib import metadata

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, select

from lightly_studio.models.database_version import DatabaseVersionTable


def validate_or_initialize_database_version(engine: Engine) -> None:
    """Validate database schema version or initialize it for fresh databases.

    These cases are handled:
    1. Fresh database with no managed tables: Insert the expected version.
    2. Existing database without a `database_version` table: Warn.
    3. Existing database with a `database_version` table:
         a. With 0 rows: Raise an error, this should not happen.
         b. With >1 rows: Raise an error, this should not happen.
         c. With 1 row and a different version: Warn about incompatible version.
         d. With 1 row and the expected version: Do nothing.

    Note that only in case 1 the version row is written. In all other cases the
    version metadata is left unchanged.

    The DB queries are executed here and not in the resolvers, as they are only used here.
    """
    existing_table_names = set(inspect(engine).get_table_names())
    SQLModel.metadata.create_all(bind=engine)
    if len(existing_table_names) == 0:
        # Case 1: Fresh database, insert the expected version.
        with Session(engine) as session:
            session.add(DatabaseVersionTable(version=metadata.version("lightly-studio")))
            session.commit()
        return

    if DatabaseVersionTable.__tablename__ not in existing_table_names:
        # Case 2: Existing database without a `database_version` table: Warn.
        logging.warning(
            f"Incompatible database schema version. Expected version "
            f"'{metadata.version('lightly-studio')}', but found missing version metadata."
        )
        return

    with Session(engine) as session:
        version_rows = session.exec(select(DatabaseVersionTable)).all()
        if len(version_rows) == 0:
            # Case 3a: Existing database with a `database_version` table but 0 rows.
            raise RuntimeError(
                "Expected exactly one row in 'database_version' when the table already "
                "exists, got 0."
            )
        if len(version_rows) > 1:
            # Case 3b: Existing database with a `database_version` table but >1 rows.
            raise RuntimeError(
                f"Expected at most one row in 'database_version' when the table already "
                f"exists, got {len(version_rows)}."
            )
        version_row = version_rows[0]
        expected_version = metadata.version("lightly-studio")
        if version_row.version != expected_version:
            # Case 3c: Existing database with a different schema version.
            logging.warning(
                f"Incompatible database schema version. Expected version "
                f"'{expected_version}', got '{version_row.version}'."
            )
        # Case 3d: Existing database with the expected schema version.
