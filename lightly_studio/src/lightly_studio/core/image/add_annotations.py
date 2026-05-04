"""Functions to add annotations to samples already present in a dataset."""

from __future__ import annotations

import logging
import posixpath
from dataclasses import dataclass
from uuid import UUID

from labelformat.model.instance_segmentation import (
    ImageInstanceSegmentation,
    InstanceSegmentationInput,
)
from labelformat.model.object_detection import (
    ImageObjectDetection,
    ObjectDetectionInput,
)
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core import labelformat_helpers
from lightly_studio.models.annotation.annotation_base import AnnotationCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_resolver,
    image_resolver,
)
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

# Constants
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch


@dataclass
class _AnnotationProcessingContext:
    """Context for processing annotations for a single sample."""

    collection_id: UUID
    sample_id: UUID
    label_map: dict[int, UUID]


def _create_label_map(
    session: Session,
    root_collection_id: UUID,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
) -> dict[int, UUID]:
    """Create a mapping of category IDs to annotation label IDs."""
    return labelformat_helpers.create_label_map(
        session=session,
        root_collection_id=root_collection_id,
        input_labels=input_labels,
    )


def _process_object_detection_annotations(
    context: _AnnotationProcessingContext,
    anno_data: ImageObjectDetection,
) -> list[AnnotationCreate]:
    """Process object detection annotations for a single image."""
    new_annotations = []
    for obj in anno_data.objects:
        new_annotations.append(
            labelformat_helpers.get_object_detection_annotation_create(
                parent_sample_id=context.sample_id,
                annotation_label_id=context.label_map[obj.category.id],
                box=obj.box,
                confidence=obj.confidence,
            )
        )
    return new_annotations


def _process_segmentation_annotations(
    context: _AnnotationProcessingContext, anno_data: ImageInstanceSegmentation
) -> list[AnnotationCreate]:
    """Process segmentation mask annotations for a single image."""
    new_annotations = []
    for obj in anno_data.objects:
        new_annotations.append(
            labelformat_helpers.get_segmentation_annotation_create(
                parent_sample_id=context.sample_id,
                annotation_label_id=context.label_map[obj.category.id],
                segmentation=obj.segmentation,
            )
        )
    return new_annotations


def add_annotations_from_labelformat(  # noqa: PLR0913
    session: Session,
    root_collection_id: UUID,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
    images_root: PathLike,
    *,
    collection_name: str | None = None,
    restrict_to_sample_ids: set[UUID] | None = None,
) -> list[str]:
    """Add annotations from a labelformat input to images already in a collection.

    This function processes annotations for images that are already present in the database,
    identified by matching their relative paths. It is useful for adding multiple annotation
    collections to the same set of images.

    Args:
        session: The database session.
        root_collection_id: The ID of the root collection containing the images.
        input_labels: The labelformat input containing images and annotations.
        images_root: The root path used to construct file_path_abs values for matching.
        collection_name: Optional name for the annotation collection. If None, a default name
            is used. Reusing the same name will append to existing annotations in that collection.
        restrict_to_sample_ids: When provided, only annotate images whose resolved sample ID
            is in this set. Used internally to restrict to newly-created images in the
            combined image+annotation path.

    Returns:
        A list of file_path_abs values from input_labels that had no matching sample in
        the collection. An empty list means all images were found.
    """
    # Create label mapping
    label_map = _create_label_map(
        session=session,
        root_collection_id=root_collection_id,
        input_labels=input_labels,
    )

    if not isinstance(input_labels, (ObjectDetectionInput, InstanceSegmentationInput)):
        raise ValueError(f"Unsupported input labels type: {type(input_labels)}")

    path_to_anno_data: dict[str, ImageInstanceSegmentation | ImageObjectDetection] = {}
    missing_paths: list[str] = []

    # Collect annotation data per batch
    for image_data in tqdm(
        input_labels.get_labels(), desc="Processing annotations", unit=" images"
    ):
        image = image_data.image  # type: ignore[attr-defined]
        typed_image_data: ImageInstanceSegmentation | ImageObjectDetection = image_data  # type: ignore[assignment]

        file_path_abs = posixpath.join(str(images_root), str(image.filename))
        path_to_anno_data[file_path_abs] = typed_image_data

        # Process batch when it reaches SAMPLE_BATCH_SIZE
        if len(path_to_anno_data) >= SAMPLE_BATCH_SIZE:
            _process_annotation_batch(
                session=session,
                root_collection_id=root_collection_id,
                path_to_anno_data=path_to_anno_data,
                label_map=label_map,
                collection_name=collection_name,
                restrict_to_sample_ids=restrict_to_sample_ids,
                missing_paths=missing_paths,
            )
            path_to_anno_data.clear()

    # Handle remaining annotations
    if path_to_anno_data:
        _process_annotation_batch(
            session=session,
            root_collection_id=root_collection_id,
            path_to_anno_data=path_to_anno_data,
            label_map=label_map,
            collection_name=collection_name,
            restrict_to_sample_ids=restrict_to_sample_ids,
            missing_paths=missing_paths,
        )

    return missing_paths


def _process_annotation_batch(  # noqa: PLR0913
    session: Session,
    root_collection_id: UUID,
    path_to_anno_data: dict[str, ImageInstanceSegmentation | ImageObjectDetection],
    label_map: dict[int, UUID],
    collection_name: str | None,
    restrict_to_sample_ids: set[UUID] | None,
    missing_paths: list[str],
) -> None:
    """Process annotations for a batch of images.

    Args:
        session: The database session.
        root_collection_id: The ID of the root collection.
        path_to_anno_data: Mapping from file path to annotation data.
        label_map: Mapping from labelformat category ID to annotation label UUID.
        collection_name: Optional name for the annotation collection.
        restrict_to_sample_ids: If provided, only process samples in this set.
        missing_paths: List to accumulate paths with no matching sample.
    """
    if not path_to_anno_data:
        return

    # Look up existing samples by path
    paths = list(path_to_anno_data.keys())
    path_to_sample_id = image_resolver.get_sample_ids_by_paths(
        session=session,
        collection_id=root_collection_id,
        file_paths_abs=paths,
    )

    # Track which sample IDs we're actually processing
    matched_sample_ids: set[UUID] = set()
    annotations_to_create: list[AnnotationCreate] = []

    for sample_path, anno_data in path_to_anno_data.items():
        if sample_path not in path_to_sample_id:
            missing_paths.append(sample_path)
            continue

        sample_id = path_to_sample_id[sample_path]

        # Skip if restricting to a specific set of sample IDs
        if restrict_to_sample_ids is not None and sample_id not in restrict_to_sample_ids:
            continue

        matched_sample_ids.add(sample_id)

        context = _AnnotationProcessingContext(
            collection_id=root_collection_id,
            sample_id=sample_id,
            label_map=label_map,
        )

        if isinstance(anno_data, ImageInstanceSegmentation):
            new_annotations = _process_segmentation_annotations(
                context=context, anno_data=anno_data
            )
        elif isinstance(anno_data, ImageObjectDetection):
            new_annotations = _process_object_detection_annotations(
                context=context, anno_data=anno_data
            )
        else:
            raise ValueError(f"Unsupported annotation data type: {type(anno_data)}")

        annotations_to_create.extend(new_annotations)

    # Create annotations (handles coverage for annotated samples)
    if annotations_to_create:
        annotation_resolver.create_many(
            session=session,
            parent_collection_id=root_collection_id,
            annotations=annotations_to_create,
            collection_name=collection_name,
        )

    # Ensure coverage is populated for all matched samples, including those with zero annotations
    if matched_sample_ids:
        annotation_collection_id = collection_resolver.get_or_create_child_collection(
            session=session,
            collection_id=root_collection_id,
            sample_type=SampleType.ANNOTATION,
            name=collection_name,
        )
        annotation_collection_coverage_resolver.add_many(
            session=session,
            annotation_collection_id=annotation_collection_id,
            parent_sample_ids=matched_sample_ids,
        )
