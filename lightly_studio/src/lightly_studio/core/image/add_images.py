"""Functions to add samples and their annotations to a dataset in the database."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

import fsspec
import PIL
from labelformat.model.image import Image
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
from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.core.loading_log import LoadingLoggingContext, log_loading_results
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    caption_resolver,
    image_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

# Constants
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch
MAX_EXAMPLE_PATHS_TO_SHOW = 5


@dataclass
class _AnnotationProcessingContext:
    """Context for processing annotations for a single sample."""

    dataset_id: UUID
    sample_id: UUID
    label_map: dict[int, UUID]


@dataclass
class AnnotationImageData:
    """Holds image data and its associated annotations."""

    annotation_type: AnnotationType
    data: ImageInstanceSegmentation | ImageObjectDetection


def load_into_dataset_from_paths(
    session: Session,
    dataset_id: UUID,
    image_paths: Iterable[str],
    show_progress: bool = True,
) -> list[UUID]:
    """Load images from file paths into the dataset.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load images into.
        image_paths: An iterable of file paths to the images to load.
        show_progress: Whether to display a progress bar and final summary of loading results.

    Returns:
        A list of UUIDs of the created samples.
    """
    samples_to_create: list[ImageCreate] = []
    created_sample_ids: list[UUID] = []

    logging_context = LoadingLoggingContext(
        n_samples_to_be_inserted=sum(1 for _ in image_paths),
        n_samples_before_loading=sample_resolver.count_by_collection_id(
            session=session, collection_id=dataset_id
        ),
    )

    for image_path in tqdm(
        image_paths,
        desc="Processing images",
        unit=" images",
        disable=not show_progress,
    ):
        try:
            with fsspec.open(image_path, "rb") as file:
                image = PIL.Image.open(file)
                width, height = image.size
                image.close()
        except (FileNotFoundError, PIL.UnidentifiedImageError, OSError):
            continue

        sample = ImageCreate(
            file_name=Path(image_path).name,
            file_path_abs=image_path,
            width=width,
            height=height,
        )
        samples_to_create.append(sample)

        # Process batch when it reaches SAMPLE_BATCH_SIZE
        if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
            created_path_to_id, paths_not_inserted = _create_batch_samples(
                session=session, collection_id=dataset_id, samples=samples_to_create
            )
            created_sample_ids.extend(created_path_to_id.values())
            logging_context.update_example_paths(paths_not_inserted)
            samples_to_create = []

    # Handle remaining samples
    if samples_to_create:
        created_path_to_id, paths_not_inserted = _create_batch_samples(
            session=session, collection_id=dataset_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())
        logging_context.update_example_paths(paths_not_inserted)

    log_loading_results(
        session=session,
        dataset_id=dataset_id,
        logging_context=logging_context,
        print_summary=show_progress,
    )
    return created_sample_ids


def load_into_dataset_from_labelformat(
    session: Session,
    dataset_id: UUID,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
    images_path: Path,
    annotation_type: AnnotationType | None = None,
) -> list[UUID]:
    """Load samples and their annotations from a labelformat input into the dataset.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load samples into.
        input_labels: The labelformat input containing images and annotations.
        images_path: The path to the directory containing the images.
        annotation_type: The type of annotations to store in the database. If None,
            it is inferred from input_labels type.
            Note: Currently (01/2026) semantic segmentation is provided as
            InstanceSegmentationInput, in that case callers need to specify
            annotation_type explicitly.

    Returns:
        A list of UUIDs of the created samples.
    """
    logging_context = LoadingLoggingContext(
        n_samples_to_be_inserted=sum(1 for _ in input_labels.get_labels()),
        n_samples_before_loading=sample_resolver.count_by_collection_id(
            session=session, collection_id=dataset_id
        ),
    )

    # Create label mapping
    label_map = _create_label_map(
        session=session,
        dataset_id=dataset_id,
        input_labels=input_labels,
    )

    samples_to_create: list[ImageCreate] = []
    created_sample_ids: list[UUID] = []
    path_to_anno_data: dict[str, AnnotationImageData] = {}

    for image_data in tqdm(input_labels.get_labels(), desc="Processing images", unit=" images"):
        image: Image = image_data.image  # type: ignore[attr-defined]

        typed_image_data: ImageInstanceSegmentation | ImageObjectDetection = image_data  # type: ignore[assignment]

        # In the first iteration, determine the annotation type if not provided.
        # Note that currently (01/2026) semantic segmentation is provided
        # as InstanceSegmentationInput, in that case callers need to specify annotation_type
        # explicitly.
        if annotation_type is None:
            if isinstance(typed_image_data, ImageInstanceSegmentation):
                annotation_type = AnnotationType.INSTANCE_SEGMENTATION
            elif isinstance(typed_image_data, ImageObjectDetection):
                annotation_type = AnnotationType.OBJECT_DETECTION
            else:
                raise ValueError(f"Unsupported annotation data type: {type(typed_image_data)}")

        sample = ImageCreate(
            file_name=str(image.filename),
            file_path_abs=str(images_path / image.filename),
            width=image.width,
            height=image.height,
        )
        samples_to_create.append(sample)
        path_to_anno_data[sample.file_path_abs] = AnnotationImageData(
            annotation_type=annotation_type,
            data=typed_image_data,
        )

        if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
            created_path_to_id, paths_not_inserted = _create_batch_samples(
                session=session, collection_id=dataset_id, samples=samples_to_create
            )
            created_sample_ids.extend(created_path_to_id.values())
            logging_context.update_example_paths(paths_not_inserted)
            _process_batch_annotations(
                session=session,
                created_path_to_id=created_path_to_id,
                path_to_anno_data=path_to_anno_data,
                dataset_id=dataset_id,
                label_map=label_map,
            )
            samples_to_create.clear()
            path_to_anno_data.clear()

    if samples_to_create:
        created_path_to_id, paths_not_inserted = _create_batch_samples(
            session=session, collection_id=dataset_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())
        logging_context.update_example_paths(paths_not_inserted)
        _process_batch_annotations(
            session=session,
            created_path_to_id=created_path_to_id,
            path_to_anno_data=path_to_anno_data,
            dataset_id=dataset_id,
            label_map=label_map,
        )

    log_loading_results(
        session=session, dataset_id=dataset_id, logging_context=logging_context, print_summary=True
    )
    return created_sample_ids


def load_into_dataset_from_coco_captions(
    session: Session,
    dataset_id: UUID,
    annotations_json: Path,
    images_path: Path,
) -> list[UUID]:
    """Load samples and captions from a COCO captions file into the dataset.

    Args:
        session: Database session used for resolver operations.
        dataset_id: Identifier of the dataset that receives the samples.
        annotations_json: Path to the COCO captions annotations file.
        images_path: Directory containing the referenced images.

    Returns:
        The list of newly created sample identifiers.
    """
    with fsspec.open(str(annotations_json), "r") as file:
        coco_payload = json.load(file)

    images: list[dict[str, object]] = coco_payload.get("images", [])
    annotations: list[dict[str, object]] = coco_payload.get("annotations", [])

    captions_by_image_id: dict[int, list[str]] = defaultdict(list)
    for annotation in annotations:
        image_id = annotation["image_id"]
        caption = annotation["caption"]
        if not isinstance(image_id, int):
            continue
        if not isinstance(caption, str):
            continue
        caption_text = caption.strip()
        if not caption_text:
            continue
        captions_by_image_id[image_id].append(caption_text)

    logging_context = LoadingLoggingContext(
        n_samples_to_be_inserted=len(images),
        n_samples_before_loading=sample_resolver.count_by_collection_id(
            session=session, collection_id=dataset_id
        ),
    )

    samples_to_create: list[ImageCreate] = []
    created_sample_ids: list[UUID] = []
    path_to_captions: dict[str, list[str]] = {}

    for image_info in tqdm(images, desc="Processing images", unit=" images"):
        if isinstance(image_info["id"], int):
            image_id_raw = image_info["id"]
        else:
            continue
        file_name_raw = str(image_info["file_name"])

        width = image_info["width"] if isinstance(image_info["width"], int) else 0
        height = image_info["height"] if isinstance(image_info["height"], int) else 0
        sample = ImageCreate(
            file_name=file_name_raw,
            file_path_abs=str(images_path / file_name_raw),
            width=width,
            height=height,
        )
        samples_to_create.append(sample)
        path_to_captions[sample.file_path_abs] = captions_by_image_id.get(image_id_raw, [])

        if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
            created_path_to_id, paths_not_inserted = _create_batch_samples(
                session=session, collection_id=dataset_id, samples=samples_to_create
            )
            created_sample_ids.extend(created_path_to_id.values())
            logging_context.update_example_paths(paths_not_inserted)
            _process_batch_captions(
                session=session,
                dataset_id=dataset_id,
                created_path_to_id=created_path_to_id,
                path_to_captions=path_to_captions,
            )
            samples_to_create.clear()
            path_to_captions.clear()

    if samples_to_create:
        created_path_to_id, paths_not_inserted = _create_batch_samples(
            session=session, collection_id=dataset_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())
        logging_context.update_example_paths(paths_not_inserted)
        _process_batch_captions(
            session=session,
            dataset_id=dataset_id,
            created_path_to_id=created_path_to_id,
            path_to_captions=path_to_captions,
        )

    log_loading_results(
        session=session, dataset_id=dataset_id, logging_context=logging_context, print_summary=True
    )
    return created_sample_ids


def tag_samples_by_directory(
    session: Session,
    collection_id: UUID,
    input_path: PathLike,
    sample_ids: list[UUID],
    tag_depth: int,
) -> None:
    """Tags samples based on their first-level subdirectory relative to input_path."""
    if tag_depth == 0:
        return
    if tag_depth > 1:
        raise NotImplementedError("tag_depth > 1 is not yet implemented for add_images_from_path.")

    input_path_abs = Path(input_path).absolute()

    newly_created_images = image_resolver.get_many_by_id(
        session=session,
        sample_ids=sample_ids,
    )
    newly_created_samples = [ImageSample(inner=image) for image in newly_created_images]

    logger.info(f"Adding directory tags to {len(sample_ids)} new samples.")
    parent_dir_to_sample_ids: defaultdict[str, list[UUID]] = defaultdict(list)
    for sample in newly_created_samples:
        sample_path_abs = Path(sample.file_path_abs)
        relative_path = sample_path_abs.relative_to(input_path_abs)

        if len(relative_path.parts) > 1:
            tag_name = relative_path.parts[0]
            if tag_name:
                parent_dir_to_sample_ids[tag_name].append(sample.sample_id)

    for tag_name, s_ids in parent_dir_to_sample_ids.items():
        tag = tag_resolver.get_or_create_sample_tag_by_name(
            session=session,
            collection_id=collection_id,
            tag_name=tag_name,
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=session,
            tag_id=tag.tag_id,
            sample_ids=s_ids,
        )
    logger.info(f"Created {len(parent_dir_to_sample_ids)} tags from directories.")


def _create_batch_samples(
    session: Session, collection_id: UUID, samples: list[ImageCreate]
) -> tuple[dict[str, UUID], list[str]]:
    """Create the batch samples.

    Args:
        session: The database session.
        collection_id: The ID of the collection to create samples in.
        samples: The samples to create.

    Returns:
        - A mapping from file paths to the created sample IDs for new samples.
        - A list of file paths that already existed in the database.
    """
    file_path_to_sample = {sample.file_path_abs: sample for sample in samples}

    # Get the list of new and existing file paths
    file_paths_new, file_paths_exist = image_resolver.filter_new_paths(
        session=session,
        collection_id=collection_id,
        file_paths_abs=list(file_path_to_sample.keys()),
    )

    # Create only samples with new file paths
    samples_to_create = [file_path_to_sample[file_path_new] for file_path_new in file_paths_new]
    created_sample_ids = image_resolver.create_many(
        session=session, collection_id=collection_id, samples=samples_to_create
    )

    # Create a mapping from file path to sample ID for new samples
    file_path_new_to_sample_id = dict(zip(file_paths_new, created_sample_ids))
    return (file_path_new_to_sample_id, file_paths_exist)


def _create_label_map(
    session: Session,
    dataset_id: UUID,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
) -> dict[int, UUID]:
    """Create a mapping of category IDs to annotation label IDs.

    Args:
        session: The database session.
        dataset_id: The ID of the root collection the labels belong to.
        input_labels: The labelformat input containing the categories.
    """
    return labelformat_helpers.create_label_map(
        session=session,
        dataset_id=dataset_id,
        input_labels=input_labels,
    )


def _process_object_detection_annotations(
    context: _AnnotationProcessingContext,
    anno_data: AnnotationImageData,
) -> list[AnnotationCreate]:
    """Process object detection annotations for a single image."""
    if not (
        anno_data.annotation_type == AnnotationType.OBJECT_DETECTION
        and isinstance(anno_data.data, ImageObjectDetection)
    ):
        raise ValueError("Invalid annotation data for object detection processing.")

    new_annotations = []
    for obj in anno_data.data.objects:
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
    context: _AnnotationProcessingContext, anno_data: AnnotationImageData
) -> list[AnnotationCreate]:
    """Process instance segmentation annotations for a single image."""
    if not (
        anno_data.annotation_type
        in (AnnotationType.INSTANCE_SEGMENTATION, AnnotationType.SEMANTIC_SEGMENTATION)
        and isinstance(anno_data.data, ImageInstanceSegmentation)
    ):
        raise ValueError("Invalid annotation data for segmentation processing.")

    annotation_type = cast(
        Literal[AnnotationType.INSTANCE_SEGMENTATION, AnnotationType.SEMANTIC_SEGMENTATION],
        anno_data.annotation_type,
    )
    new_annotations = []
    for obj in anno_data.data.objects:
        new_annotations.append(
            labelformat_helpers.get_segmentation_annotation_create(
                parent_sample_id=context.sample_id,
                annotation_label_id=context.label_map[obj.category.id],
                segmentation=obj.segmentation,
                annotation_type=annotation_type,
            )
        )
    return new_annotations


def _process_batch_annotations(
    session: Session,
    created_path_to_id: Mapping[str, UUID],
    path_to_anno_data: Mapping[str, AnnotationImageData],
    dataset_id: UUID,
    label_map: dict[int, UUID],
) -> None:
    """Process annotations for a batch of samples."""
    if len(created_path_to_id) == 0:
        return

    annotations_to_create: list[AnnotationCreate] = []

    for sample_path, sample_id in created_path_to_id.items():
        anno_data = path_to_anno_data[sample_path]

        context = _AnnotationProcessingContext(
            dataset_id=dataset_id,
            sample_id=sample_id,
            label_map=label_map,
        )

        if anno_data.annotation_type in (
            AnnotationType.INSTANCE_SEGMENTATION,
            AnnotationType.SEMANTIC_SEGMENTATION,
        ):
            new_annotations = _process_segmentation_annotations(
                context=context, anno_data=anno_data
            )
        elif anno_data.annotation_type == AnnotationType.OBJECT_DETECTION:
            new_annotations = _process_object_detection_annotations(
                context=context, anno_data=anno_data
            )
        else:
            raise ValueError(f"Unsupported annotation type: {anno_data.annotation_type}")

        annotations_to_create.extend(new_annotations)

    annotation_resolver.create_many(
        session=session, parent_collection_id=dataset_id, annotations=annotations_to_create
    )


def _process_batch_captions(
    session: Session,
    dataset_id: UUID,
    created_path_to_id: Mapping[str, UUID],
    path_to_captions: Mapping[str, list[str]],
) -> None:
    """Process captions for a batch of samples."""
    if len(created_path_to_id) == 0:
        return

    captions_to_create: list[CaptionCreate] = []

    for sample_path, sample_id in created_path_to_id.items():
        captions = path_to_captions[sample_path]
        if not captions:
            continue

        for caption_text in captions:
            caption = CaptionCreate(
                parent_sample_id=sample_id,
                text=caption_text,
            )
            captions_to_create.append(caption)

    caption_resolver.create_many(
        session=session, parent_collection_id=dataset_id, captions=captions_to_create
    )
