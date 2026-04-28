"""Register an existing annotation child collection as a ground-truth AnnotationCollection."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation_collection import AnnotationCollectionTable
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_collection_resolver
from lightly_studio.resolvers.collection_resolver import get_or_create_child_collection

logger = logging.getLogger(__name__)


def register_annotation_collection(
    session: Session,
    dataset_id: UUID,
    root_collection_id: UUID,
    collection_name: str,
    is_ground_truth: bool = False,
    processed_sample_count: int | None = None,
    notes: str | None = None,
) -> AnnotationCollectionTable:
    """Ensure an AnnotationCollectionTable entry exists for a named annotation group.

    Idempotent — safe to call after each `add_samples_from_coco(...)` call.
    """
    existing = annotation_collection_resolver.get_by_name(
        session=session, dataset_id=dataset_id, name=collection_name
    )
    if existing is not None:
        return existing

    annotation_child_collection_id = get_or_create_child_collection(
        session=session,
        collection_id=root_collection_id,
        sample_type=SampleType.ANNOTATION,
        name=collection_name,
    )

    return annotation_collection_resolver.create(
        session=session,
        dataset_id=dataset_id,
        collection_id=annotation_child_collection_id,
        name=collection_name,
        is_ground_truth=is_ground_truth,
        processed_sample_count=processed_sample_count,
        notes=notes,
    )
