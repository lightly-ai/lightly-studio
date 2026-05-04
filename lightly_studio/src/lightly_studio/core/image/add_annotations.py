"""Functions to add annotations to samples already present in a dataset."""

from __future__ import annotations

import posixpath
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID

import fsspec
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

# Constants
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch


def add_annotations_from_labelformat(  # noqa: PLR0913
    session: Session,
    root_collection_id: UUID,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
    images_root: PathLike,
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
    images_root_abs = normalize_images_root(images_root=images_root)
    label_map = labelformat_helpers.create_label_map(
        session=session,
        root_collection_id=root_collection_id,
        input_labels=input_labels,
    )

    path_to_anno_data: dict[str, ImageInstanceSegmentation | ImageObjectDetection] = {}
    missing_paths: list[str] = []

    for image_data in tqdm(
        input_labels.get_labels(), desc="Processing annotations", unit=" images"
    ):
        annotation_data: ImageInstanceSegmentation | ImageObjectDetection = image_data  # type: ignore[assignment]
        file_path_abs = posixpath.join(images_root_abs, str(annotation_data.image.filename))
        path_to_anno_data[file_path_abs] = annotation_data

        if len(path_to_anno_data) >= SAMPLE_BATCH_SIZE:
            missing_paths.extend(
                _process_annotation_batch(
                    session=session,
                    root_collection_id=root_collection_id,
                    path_to_anno_data=path_to_anno_data,
                    label_map=label_map,
                    collection_name=collection_name,
                    restrict_to_sample_ids=restrict_to_sample_ids,
                )
            )
            path_to_anno_data.clear()

    if path_to_anno_data:
        missing_paths.extend(
            _process_annotation_batch(
                session=session,
                root_collection_id=root_collection_id,
                path_to_anno_data=path_to_anno_data,
                label_map=label_map,
                collection_name=collection_name,
                restrict_to_sample_ids=restrict_to_sample_ids,
            )
        )

    return missing_paths


def normalize_images_root(images_root: PathLike) -> str:
    """Return absolute local roots and preserve remote roots."""
    images_root_str = str(images_root)
    protocol, _ = fsspec.core.split_protocol(images_root_str)
    if protocol is None:
        return str(Path(images_root_str).absolute())
    if protocol == "file":
        return str(Path(fsspec.core.strip_protocol(images_root_str)).absolute())
    return images_root_str


def _process_annotation_batch(  # noqa: PLR0913
    session: Session,
    root_collection_id: UUID,
    path_to_anno_data: Mapping[str, ImageInstanceSegmentation | ImageObjectDetection],
    label_map: dict[int, UUID],
    collection_name: str | None,
    restrict_to_sample_ids: set[UUID] | None,
) -> list[str]:
    """Process annotations for a batch of images.

    Args:
        session: The database session.
        root_collection_id: The ID of the root collection.
        path_to_anno_data: Mapping from file path to annotation data.
        label_map: Mapping from labelformat category ID to annotation label UUID.
        collection_name: Optional name for the annotation collection.
        restrict_to_sample_ids: If provided, only process samples in this set.

    Returns:
        Paths with no matching sample in the collection.
    """
    if not path_to_anno_data:
        return []

    path_to_sample_id = image_resolver.get_sample_ids_by_paths(
        session=session,
        collection_id=root_collection_id,
        file_paths_abs=list(path_to_anno_data.keys()),
    )
    matched_sample_ids: set[UUID] = set()
    annotations_to_create: list[AnnotationCreate] = []
    missing_paths: list[str] = []

    for sample_path, anno_data in path_to_anno_data.items():
        sample_id = path_to_sample_id.get(sample_path)
        if sample_id is None:
            missing_paths.append(sample_path)
            continue

        if restrict_to_sample_ids is not None and sample_id not in restrict_to_sample_ids:
            continue

        matched_sample_ids.add(sample_id)
        annotations_to_create.extend(
            _get_annotation_creates(
                sample_id=sample_id,
                label_map=label_map,
                anno_data=anno_data,
            )
        )

    if annotations_to_create:
        annotation_resolver.create_many(
            session=session,
            parent_collection_id=root_collection_id,
            annotations=annotations_to_create,
            collection_name=collection_name,
        )

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

    return missing_paths


def _get_annotation_creates(
    sample_id: UUID,
    label_map: dict[int, UUID],
    anno_data: ImageInstanceSegmentation | ImageObjectDetection,
) -> list[AnnotationCreate]:
    """Create annotation inputs for a single image sample."""
    if isinstance(anno_data, ImageInstanceSegmentation):
        return [
            labelformat_helpers.get_segmentation_annotation_create(
                parent_sample_id=sample_id,
                annotation_label_id=label_map[obj.category.id],
                segmentation=obj.segmentation,
            )
            for obj in anno_data.objects
        ]

    return [
        labelformat_helpers.get_object_detection_annotation_create(
            parent_sample_id=sample_id,
            annotation_label_id=label_map[obj.category.id],
            box=obj.box,
            confidence=obj.confidence,
        )
        for obj in anno_data.objects
    ]
