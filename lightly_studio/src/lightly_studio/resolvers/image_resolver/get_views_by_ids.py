"""Implementation of get_view_by_id function for image."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.models.caption import CaptionView
from lightly_studio.models.image import ImageView
from lightly_studio.models.metadata import SampleMetadataView
from lightly_studio.models.sample import SampleView
from lightly_studio.resolvers import image_resolver


def get_views_by_ids(session: Session, sample_ids: list[UUID]) -> list[ImageView]:
    """Get the views for a list of sample_ids.

    Args:
        session: The database session.
        sample_ids: The IDs of the images to retrieve.

    Returns:
        The views for the given image IDs.
    """
    images = image_resolver.get_many_by_id(session=session, sample_ids=sample_ids)

    if not images:
        raise ValueError(f"Images with sample_ids '{sample_ids}' not found.")

    return [
        ImageView(
            file_name=image.file_name,
            file_path_abs=image.file_path_abs,
            sample_id=image.sample_id,
            annotations=[
                AnnotationView.from_annotation_table(annotation=annotation)
                for annotation in image.sample.annotations
            ],
            captions=[CaptionView.model_validate(caption) for caption in image.sample.captions],
            tags=[
                ImageView.ImageViewTag(
                    tag_id=tag.tag_id,
                    name=tag.name,
                    kind=tag.kind,
                    created_at=tag.created_at,
                    updated_at=tag.updated_at,
                )
                for tag in image.sample.tags
            ],
            metadata_dict=SampleMetadataView.model_validate(image.sample.metadata_dict)
            if image.sample.metadata_dict
            else None,
            width=image.width,
            height=image.height,
            sample=SampleView.model_validate(image.sample),
        )
        for image in images
    ]
