"""Query language: text → Lark parse tree → MatchExpression → SQLAlchemy.

Public API::

    from lightly_studio.core.query_language import parse_query, execute_query

    # Parse + compile to MatchExpression
    from lightly_studio.core.query_language import FieldRegistry
    registry = FieldRegistry()
    match_expr = parse_query('width > 100 and has_tag("train")', registry)
    sql_condition = match_expr.get()  # ColumnElement[bool]

    # End-to-end execution
    samples, count = execute_query(
        text='width > 100 and has_tag("train")',
        session=session,
        collection_id=collection_id,
        sample_type=SampleType.image,
    )
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.core.query_language.field_registry import FieldRegistry
from lightly_studio.core.query_language.parser import parse_query
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable

__all__ = ["FieldRegistry", "execute_query", "parse_query"]


def execute_query(
    text: str,
    session: Session,
    collection_id: UUID,
    sample_type: SampleType,  # noqa: ARG001
    pagination: Paginated | None = None,
) -> tuple[list[Any], int]:
    """Parse and execute a query string against the database.

    Args:
        text: The query text to execute.
        session: An active database session.
        collection_id: The collection to query within.
        sample_type: Sample type (currently only image is supported).
        pagination: Optional offset/limit pagination.

    Returns:
        ``(samples, total_count)`` where *samples* is a list of
        ``ImageTable`` rows matching the query.

    Raises:
        lark.exceptions.LarkError: On parse failure.
        ValueError: On unknown fields or operators.
    """
    registry = FieldRegistry()
    condition = parse_query(text, registry).get()

    samples_query = (
        select(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
        .where(condition)
        .order_by(col(ImageTable.file_path_abs).asc())
    )
    count_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
        .where(condition)
    )

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(count_query).one()
    samples = list(session.exec(samples_query).all())
    return samples, total_count
