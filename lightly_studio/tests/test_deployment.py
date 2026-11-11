from __future__ import annotations

from sqlmodel import Session

from lightly_studio import deployment


def test_is_enterprise(db_session: Session, postgres_url: str | None) -> None:
    # The PostgreSQL suite sets postgres_url, the default suite runs on DuckDB
    assert deployment.is_enterprise(session=db_session) is (postgres_url is not None)
