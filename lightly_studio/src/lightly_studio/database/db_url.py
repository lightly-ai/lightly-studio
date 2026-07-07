"""Database URL helpers."""

from __future__ import annotations

import re


def ensure_psycopg3_driver(engine_url: str) -> str:
    """Rewrite Postgres URLs to use the psycopg3 driver.

    SQLAlchemy defaults to psycopg2 for ``postgresql://`` URLs. This rewrites
    the URL to use ``postgresql+psycopg://`` so that the psycopg3 driver is
    selected instead.

    Args:
        engine_url: The database engine URL.

    Returns:
        The URL with the psycopg3 driver specified when the scheme is Postgres.
    """
    return re.sub(r"^(postgresql|postgres)://", "postgresql+psycopg://", engine_url)
