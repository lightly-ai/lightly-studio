"""Embed the crops of annotations that the GUI creates or changes."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.database import db_manager
from lightly_studio.embed import embed_samples
from lightly_studio.models.annotation.annotation_base import CROPPABLE_ANNOTATION_TYPES
from lightly_studio.resolvers import annotation_resolver

logger = logging.getLogger(__name__)


def embed_annotation_crops(session: Session, annotation_ids: Sequence[UUID]) -> None:
    """Embed the crops of annotations and replace their old embeddings.

    Annotations without a crop, such as classifications, are ignored. Nothing is embedded
    when the annotation collection and its parent have no default embedding model.

    Args:
        session: Database session for executing the operation.
        annotation_ids: The annotations to embed.
    """
    annotations = annotation_resolver.get_by_ids(session=session, annotation_ids=annotation_ids)
    ids_by_collection: dict[UUID, list[UUID]] = {}
    for annotation in annotations:
        if annotation.annotation_type in CROPPABLE_ANNOTATION_TYPES:
            ids_by_collection.setdefault(annotation.annotation_collection_id, []).append(
                annotation.sample_id
            )
    for annotation_collection_id, annotation_sample_ids in ids_by_collection.items():
        embed_samples.embed_annotations(
            session=session,
            annotation_collection_id=annotation_collection_id,
            annotation_sample_ids=annotation_sample_ids,
        )


def embed_annotation_crops_in_background(annotation_ids: Sequence[UUID]) -> None:
    """Run ``embed_annotation_crops`` in its own session and log a failure.

    A request schedules this as a background task, so it opens a new session and does not
    raise: the annotation edit is already saved.

    Args:
        annotation_ids: The annotations to embed.
    """
    try:
        with db_manager.session() as session:
            embed_annotation_crops(session=session, annotation_ids=annotation_ids)
    except Exception:
        logger.exception("Could not embed the crops of annotations %s.", list(annotation_ids))
