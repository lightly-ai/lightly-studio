from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
)


def create_source_annotations(
    session: Session, image: ImageTable, source_name: str, count: int
) -> list[AnnotationBaseTable]:
    """Create count boxes on the image in the named annotation source.

    The boxes get a new annotation class with the name of the source.
    """
    collection_id = image.sample.collection_id
    label = create_annotation_label(
        session=session, root_collection_id=collection_id, label_name=source_name
    )
    details = AnnotationDetails(
        sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
    )
    return create_annotations(
        session=session,
        collection_id=collection_id,
        annotations=[details] * count,
        collection_name=source_name,
    )
