"""Functions to add samples and their annotations to a dataset in the database."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from uuid import UUID

import fsspec
import PIL
from labelformat.model.binary_mask_segmentation import BinaryMaskSegmentation
from labelformat.model.bounding_box import BoundingBoxFormat
from labelformat.model.image import Image
from labelformat.model.instance_segmentation import (
    ImageInstanceSegmentation,
    InstanceSegmentationInput,
)
from labelformat.model.multipolygon import MultiPolygon
from labelformat.model.object_detection import (
    ImageObjectDetection,
    ObjectDetectionInput,
)
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.models.annotation.annotation_base import AnnotationCreate
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    caption_resolver,
    image_resolver,
    sample_resolver,
)

# Constants
ANNOTATION_BATCH_SIZE = 64  # Number of annotations to process in a single batch
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch
MAX_EXAMPLE_PATHS_TO_SHOW = 5


@dataclass
class _AnnotationProcessingContext:
    """Context for processing annotations for a single sample."""

    dataset_id: UUID
    sample_id: UUID
    label_map: dict[int, UUID]


@dataclass
class _LoadingLoggingContext:
    """Context for the logging while loading data."""

    n_samples_before_loading: int
    n_samples_to_be_inserted: int = 0
    example_paths_not_inserted: list[str] = field(default_factory=list)

    def update_example_paths(self, example_paths_not_inserted: list[str]) -> None:
        if len(self.example_paths_not_inserted) >= MAX_EXAMPLE_PATHS_TO_SHOW:
            return
        upper_limit = MAX_EXAMPLE_PATHS_TO_SHOW - len(self.example_paths_not_inserted)
        self.example_paths_not_inserted.extend(example_paths_not_inserted[:upper_limit])


def load_into_dataset_from_paths(
    session: Session,
    dataset_id: UUID,
    image_paths: Iterable[str],
) -> list[UUID]:
    """Load images from file paths into the dataset.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load images into.
        image_paths: An iterable of file paths to the images to load.

    Returns:
        A list of UUIDs of the created samples.
    """
    samples_to_create: list[ImageCreate] = []
    created_sample_ids: list[UUID] = []

    logging_context = _LoadingLoggingContext(
        n_samples_to_be_inserted=sum(1 for _ in image_paths),
        n_samples_before_loading=sample_resolver.count_by_dataset_id(
            session=session, dataset_id=dataset_id
        ),
    )

    for image_path in tqdm(
        image_paths,
        desc="Processing images",
        unit=" images",
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
                session=session, dataset_id=dataset_id, samples=samples_to_create
            )
            created_sample_ids.extend(created_path_to_id.values())
            logging_context.update_example_paths(paths_not_inserted)
            samples_to_create = []

    # Handle remaining samples
    if samples_to_create:
        created_path_to_id, paths_not_inserted = _create_batch_samples(
            session=session, dataset_id=dataset_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())
        logging_context.update_example_paths(paths_not_inserted)

    _log_loading_results(session=session, dataset_id=dataset_id, logging_context=logging_context)
    return created_sample_ids


def load_into_dataset_from_labelformat(
    session: Session,
    dataset_id: UUID,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
    images_path: Path,
) -> list[UUID]:
    """Load samples and their annotations from a labelformat input into the dataset.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to load samples into.
        input_labels: The labelformat input containing images and annotations.
        images_path: The path to the directory containing the images.

    Returns:
        A list of UUIDs of the created samples.
    """
    logging_context = _LoadingLoggingContext(
        n_samples_to_be_inserted=sum(1 for _ in input_labels.get_labels()),
        n_samples_before_loading=sample_resolver.count_by_dataset_id(
            session=session, dataset_id=dataset_id
        ),
    )

    # Create label mapping
    label_map = _create_label_map(session=session, input_labels=input_labels)

    annotations_to_create: list[AnnotationCreate] = []
    samples_to_create: list[ImageCreate] = []
    created_sample_ids: list[UUID] = []
    path_to_anno_data: dict[str, ImageInstanceSegmentation | ImageObjectDetection] = {}

    for image_data in tqdm(input_labels.get_labels(), desc="Processing images", unit=" images"):
        image: Image = image_data.image  # type: ignore[attr-defined]

        typed_image_data: ImageInstanceSegmentation | ImageObjectDetection = image_data  # type: ignore[assignment]
        sample = ImageCreate(
            file_name=str(image.filename),
            file_path_abs=str(images_path / image.filename),
            width=image.width,
            height=image.height,
        )
        samples_to_create.append(sample)
        path_to_anno_data[sample.file_path_abs] = typed_image_data

        if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
            created_path_to_id, paths_not_inserted = _create_batch_samples(
                session=session, dataset_id=dataset_id, samples=samples_to_create
            )
            created_sample_ids.extend(created_path_to_id.values())
            logging_context.update_example_paths(paths_not_inserted)
            _process_batch_annotations(
                session=session,
                created_path_to_id=created_path_to_id,
                path_to_anno_data=path_to_anno_data,
                dataset_id=dataset_id,
                label_map=label_map,
                annotations_to_create=annotations_to_create,
            )
            samples_to_create.clear()
            path_to_anno_data.clear()

    if samples_to_create:
        created_path_to_id, paths_not_inserted = _create_batch_samples(
            session=session, dataset_id=dataset_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())
        logging_context.update_example_paths(paths_not_inserted)
        _process_batch_annotations(
            session=session,
            created_path_to_id=created_path_to_id,
            path_to_anno_data=path_to_anno_data,
            dataset_id=dataset_id,
            label_map=label_map,
            annotations_to_create=annotations_to_create,
        )

    # Insert any remaining annotations
    if annotations_to_create:
        annotation_resolver.create_many(session=session, annotations=annotations_to_create)

    _log_loading_results(session=session, dataset_id=dataset_id, logging_context=logging_context)

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

    logging_context = _LoadingLoggingContext(
        n_samples_to_be_inserted=len(images),
        n_samples_before_loading=sample_resolver.count_by_dataset_id(
            session=session, dataset_id=dataset_id
        ),
    )

    captions_to_create: list[CaptionCreate] = []
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
                session=session, dataset_id=dataset_id, samples=samples_to_create
            )
            created_sample_ids.extend(created_path_to_id.values())
            logging_context.update_example_paths(paths_not_inserted)
            _process_batch_captions(
                session=session,
                dataset_id=dataset_id,
                created_path_to_id=created_path_to_id,
                path_to_captions=path_to_captions,
                captions_to_create=captions_to_create,
            )
            samples_to_create.clear()
            path_to_captions.clear()

    if samples_to_create:
        created_path_to_id, paths_not_inserted = _create_batch_samples(
            session=session, dataset_id=dataset_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())
        logging_context.update_example_paths(paths_not_inserted)
        _process_batch_captions(
            session=session,
            dataset_id=dataset_id,
            created_path_to_id=created_path_to_id,
            path_to_captions=path_to_captions,
            captions_to_create=captions_to_create,
        )

    if captions_to_create:
        caption_resolver.create_many(session=session, captions=captions_to_create)

    _log_loading_results(session=session, dataset_id=dataset_id, logging_context=logging_context)

    return created_sample_ids


def _log_loading_results(
    session: Session, dataset_id: UUID, logging_context: _LoadingLoggingContext
) -> None:
    n_samples_end = sample_resolver.count_by_dataset_id(session=session, dataset_id=dataset_id)
    n_samples_inserted = n_samples_end - logging_context.n_samples_before_loading
    print(
        f"Added {n_samples_inserted} out of {logging_context.n_samples_to_be_inserted}"
        " new samples to the dataset."
    )
    if logging_context.example_paths_not_inserted:
        # TODO(Jonas, 09/2025): Use logging instead of print
        print(
            f"Examples of paths that were not added: "
            f" {', '.join(logging_context.example_paths_not_inserted)}"
        )


def _create_batch_samples(
    session: Session, dataset_id: UUID, samples: list[ImageCreate]
) -> tuple[dict[str, UUID], list[str]]:
    """Create the batch samples.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to create samples in.
        samples: The samples to create.

    Returns:
        - A mapping from file paths to the created sample IDs for new samples.
        - A list of file paths that already existed in the database.
    """
    file_path_to_sample = {sample.file_path_abs: sample for sample in samples}

    # Get the list of new and existing file paths
    file_paths_new, file_paths_exist = image_resolver.filter_new_paths(
        session=session, file_paths_abs=list(file_path_to_sample.keys())
    )

    # Create only samples with new file paths
    samples_to_create = [file_path_to_sample[file_path_new] for file_path_new in file_paths_new]
    created_sample_ids = image_resolver.create_many(
        session=session, dataset_id=dataset_id, samples=samples_to_create
    )

    # Create a mapping from file path to sample ID for new samples
    file_path_new_to_sample_id = dict(zip(file_paths_new, created_sample_ids))
    return (file_path_new_to_sample_id, file_paths_exist)


def _create_label_map(
    session: Session,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
) -> dict[int, UUID]:
    """Create a mapping of category IDs to annotation label IDs."""
    label_map = {}
    for category in tqdm(
        input_labels.get_categories(),
        desc="Processing categories",
        unit=" categories",
    ):
        # Use label if already exists
        label = annotation_label_resolver.get_by_label_name(
            session=session, label_name=category.name
        )
        if label is None:
            # Create new label
            label_create = AnnotationLabelCreate(annotation_label_name=category.name)
            label = annotation_label_resolver.create(session=session, label=label_create)

        label_map[category.id] = label.annotation_label_id
    return label_map


def _process_object_detection_annotations(
    context: _AnnotationProcessingContext,
    anno_data: ImageObjectDetection,
) -> list[AnnotationCreate]:
    """Process object detection annotations for a single image."""
    new_annotations = []
    for obj in anno_data.objects:
        box = obj.box.to_format(BoundingBoxFormat.XYWH)
        x, y, width, height = box

        new_annotations.append(
            AnnotationCreate(
                dataset_id=context.dataset_id,
                parent_sample_id=context.sample_id,
                annotation_label_id=context.label_map[obj.category.id],
                annotation_type="object_detection",
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                confidence=obj.confidence,
            )
        )
    return new_annotations


def _process_instance_segmentation_annotations(
    context: _AnnotationProcessingContext,
    anno_data: ImageInstanceSegmentation,
) -> list[AnnotationCreate]:
    """Process instance segmentation annotations for a single image."""
    new_annotations = []
    for obj in anno_data.objects:
        segmentation_rle: None | list[int] = None
        if isinstance(obj.segmentation, MultiPolygon):
            box = obj.segmentation.bounding_box().to_format(BoundingBoxFormat.XYWH)
        elif isinstance(obj.segmentation, BinaryMaskSegmentation):
            box = obj.segmentation.bounding_box.to_format(BoundingBoxFormat.XYWH)
            segmentation_rle = obj.segmentation._rle_row_wise  # noqa: SLF001
        else:
            raise ValueError(f"Unsupported segmentation type: {type(obj.segmentation)}")

        x, y, width, height = box

        new_annotations.append(
            AnnotationCreate(
                dataset_id=context.dataset_id,
                parent_sample_id=context.sample_id,
                annotation_label_id=context.label_map[obj.category.id],
                annotation_type="instance_segmentation",
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                segmentation_mask=segmentation_rle,
            )
        )
    return new_annotations


def _process_batch_annotations(  # noqa: PLR0913
    session: Session,
    created_path_to_id: dict[str, UUID],
    path_to_anno_data: dict[str, ImageInstanceSegmentation | ImageObjectDetection],
    dataset_id: UUID,
    label_map: dict[int, UUID],
    annotations_to_create: list[AnnotationCreate],
) -> None:
    """Process annotations for a batch of samples."""
    for sample_path, sample_id in created_path_to_id.items():
        anno_data = path_to_anno_data[sample_path]

        context = _AnnotationProcessingContext(
            dataset_id=dataset_id,
            sample_id=sample_id,
            label_map=label_map,
        )

        if isinstance(anno_data, ImageInstanceSegmentation):
            new_annotations = _process_instance_segmentation_annotations(
                context=context, anno_data=anno_data
            )
        elif isinstance(anno_data, ImageObjectDetection):
            new_annotations = _process_object_detection_annotations(
                context=context, anno_data=anno_data
            )
        else:
            raise ValueError(f"Unsupported annotation type: {type(anno_data)}")

        annotations_to_create.extend(new_annotations)

        if len(annotations_to_create) >= ANNOTATION_BATCH_SIZE:
            annotation_resolver.create_many(session=session, annotations=annotations_to_create)
            annotations_to_create.clear()


def _process_batch_captions(
    session: Session,
    dataset_id: UUID,
    created_path_to_id: dict[str, UUID],
    path_to_captions: dict[str, list[str]],
    captions_to_create: list[CaptionCreate],
) -> None:
    """Process captions for a batch of samples."""
    if not created_path_to_id:
        return

    for sample_path, sample_id in created_path_to_id.items():
        captions = path_to_captions[sample_path]
        if not captions:
            continue

        for caption_text in captions:
            caption = CaptionCreate(
                dataset_id=dataset_id,
                parent_sample_id=sample_id,
                text=caption_text,
            )
            captions_to_create.append(caption)

        if len(captions_to_create) >= ANNOTATION_BATCH_SIZE:
            caption_resolver.create_many(session=session, captions=captions_to_create)
            captions_to_create.clear()
