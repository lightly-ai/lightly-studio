"""Resolve the value type of metadata sorts from the stored metadata schema."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByMetadataField
from lightly_studio.database import db_json
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable


def resolve_cast_to_float(
    session: Session,
    collection_id: UUID,
    order_by: Sequence[OrderByExpression],
) -> None:
    """Set the numeric cast on every metadata sort in ``order_by``.

    Numeric metadata has to be cast to float before ordering, otherwise the extracted
    JSON values sort lexicographically ("10" before "9"). The value type is already
    recorded per key in ``SampleMetadataTable.metadata_schema``, so callers do not have
    to know it. Keys missing from the schema keep lexicographic ordering.

    Args:
        session: The database session.
        collection_id: The collection whose metadata schema to read.
        order_by: The sort expressions to resolve. Non-metadata sorts are left untouched.
    """
    for expression in order_by:
        if isinstance(expression, OrderByMetadataField):
            expression.infer_cast_to_float(
                metadata_type=_get_metadata_type_for_key(
                    session=session,
                    collection_id=collection_id,
                    key=expression.field_name,
                )
            )


def _get_metadata_type_for_key(
    session: Session,
    collection_id: UUID,
    key: str,
) -> str | None:
    """Get the schema type recorded for one metadata key in a collection.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        key: The metadata key to look up.

    Returns:
        The type name (e.g. ``"integer"``, ``"float"``, ``"string"``), or ``None`` if no
        sample in the collection records the key.
    """
    schema_type_expr = db_json.json_extract_string(
        column=SampleMetadataTable.metadata_schema,
        field=key,
    )
    # ``MetadataBase.ensure_schema`` rejects values that disagree with the type already
    # recorded for a key, so a single row is enough to determine it.
    return session.exec(
        select(schema_type_expr)
        .select_from(SampleTable)
        .join(
            SampleMetadataTable,
            col(SampleMetadataTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            SampleTable.collection_id == collection_id,
            schema_type_expr.isnot(None),
        )
        .limit(1)
    ).first()
