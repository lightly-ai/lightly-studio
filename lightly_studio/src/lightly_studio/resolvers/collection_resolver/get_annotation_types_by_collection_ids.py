"""Resolve the distinct annotation types contained in annotation collections."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable


def get_annotation_types_by_collection_ids(
    session: Session,
    collection_ids: Sequence[UUID],
) -> dict[UUID, list[str]]:
    """Return the distinct annotation types present in each annotation collection.

    Annotations belong to a collection through their sample's ``collection_id``
    (mirrors the join used by the evaluation validators).

    Args:
        session: The database session.
        collection_ids: Annotation collection IDs to inspect.

    Returns:
        Mapping of collection ID to the sorted list of distinct annotation type
        values (e.g. ``["object_detection"]``). Collections without annotations
        are omitted.
    """
    if not collection_ids:
        return {}

    sample = aliased(SampleTable)
    statement = (
        select(col(sample.collection_id), col(AnnotationBaseTable.annotation_type))
        .join(sample, AnnotationBaseTable.sample)
        .where(col(sample.collection_id).in_(collection_ids))
        .distinct()
    )

    result: dict[UUID, list[str]] = {}
    for collection_id, annotation_type in session.exec(statement).all():
        result.setdefault(collection_id, []).append(annotation_type.value)
    for types in result.values():
        types.sort()
    return result
