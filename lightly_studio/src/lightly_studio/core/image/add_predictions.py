"""Load Lightly-format predictions into the DB as a named AnnotationCollection."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from labelformat.formats import LightlyObjectDetectionInput
from sqlmodel import Session, col, select

from lightly_studio.core import labelformat_helpers
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_collection import AnnotationCollectionTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import annotation_collection_resolver
from lightly_studio.resolvers.annotation_resolver import create_many
from lightly_studio.resolvers.collection_resolver import get_or_create_child_collection

logger = logging.getLogger(__name__)


def add_predictions_from_lightly(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    root_collection_id: UUID,
    input_folder: Path,
    collection_name: str,
    images_rel_path: str = "../images",
) -> AnnotationCollectionTable:
    """Load Lightly-format predictions and register them as a named AnnotationCollection.

    Unlike add_samples_from_lightly, this method adds annotations to EXISTING images.
    Images not found in the DB are skipped with a warning.

    The Lightly prediction format supports confidence scores natively via the
    ``score`` field in each annotation JSON file.

    Args:
        session: Active database session.
        dataset_id: ID of the dataset to load predictions into.
        root_collection_id: Root collection of the dataset.
        input_folder: Folder containing the Lightly annotation files (.json per image).
        collection_name: Name for this prediction set (e.g. "YOLOv8-n epoch 50").
        images_rel_path: Relative path from input_folder to the images directory.
    """
    existing = annotation_collection_resolver.get_by_name(
        session=session, dataset_id=dataset_id, name=collection_name
    )
    if existing is not None:
        logger.warning(
            "Annotation collection '%s' already exists — skipping import.", collection_name
        )
        return existing

    label_input = LightlyObjectDetectionInput(
        input_folder=input_folder, images_rel_path=images_rel_path
    )

    label_map = labelformat_helpers.create_label_map(
        session=session,
        root_collection_id=root_collection_id,
        input_labels=label_input,
    )

    all_filenames = [str(img.filename) for img in label_input.get_images()]
    stmt = select(ImageTable).where(col(ImageTable.file_name).in_(all_filenames))
    filename_to_sample_id: dict[str, UUID] = {
        img.file_name: img.sample_id for img in session.exec(stmt).all()
    }

    annotations: list[AnnotationCreate] = []
    skipped = 0
    for image_det in label_input.get_labels():
        file_name = str(image_det.image.filename)
        parent_sample_id = filename_to_sample_id.get(file_name)
        if parent_sample_id is None:
            skipped += 1
            continue

        for obj in image_det.objects:
            bbox = obj.box
            annotations.append(
                AnnotationCreate(
                    annotation_label_id=label_map[obj.category.id],
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    confidence=obj.confidence,
                    parent_sample_id=parent_sample_id,
                    x=int(bbox.xmin),
                    y=int(bbox.ymin),
                    width=int(bbox.xmax - bbox.xmin),
                    height=int(bbox.ymax - bbox.ymin),
                )
            )

    if skipped:
        logger.warning("Skipped annotations for %d images not found in the dataset.", skipped)

    annotation_child_collection_id = get_or_create_child_collection(
        session=session,
        collection_id=root_collection_id,
        sample_type=SampleType.ANNOTATION,
        name=collection_name,
    )

    if annotations:
        create_many(
            session=session,
            parent_collection_id=root_collection_id,
            annotations=annotations,
            collection_name=collection_name,
        )

    logger.info("Loaded %d predictions into '%s'.", len(annotations), collection_name)

    return annotation_collection_resolver.create(
        session=session,
        dataset_id=dataset_id,
        collection_id=annotation_child_collection_id,
        name=collection_name,
        is_ground_truth=False,
    )
