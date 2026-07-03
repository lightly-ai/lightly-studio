"""Functions to add samples and their annotations to a dataset in the database."""

from __future__ import annotations

import itertools
import json
import logging
import posixpath
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from uuid import UUID

import fsspec
import PIL
from labelformat.model.image import Image
from labelformat.model.instance_segmentation import (
    InstanceSegmentationInput,
)
from labelformat.model.object_detection import ObjectDetectionInput
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import (
    AlreadyPresentInputFileError,
    FileOutcomeReport,
)
from lightly_studio.core.image import add_annotations
from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import (
    caption_resolver,
    image_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

# Constants
SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch


def load_into_dataset_from_paths(
    session: Session,
    root_collection_id: UUID,
    image_paths: Iterable[str],
    show_progress: bool = True,
) -> list[UUID]:
    """Load images from file paths into the dataset.

    Args:
        session: The database session.
        root_collection_id: The ID of the dataset to load images into.
        image_paths: An iterable of file paths to the images to load.
        show_progress: Whether to display a progress bar and final summary of loading results.

    Returns:
        A list of UUIDs of the created samples.
    """
    # Normalize all paths up front so the database check can happen once, before the
    # main processing loop, instead of once per batch.
    normalized_paths = [
        add_annotations.normalize_images_root(image_path) for image_path in image_paths
    ]
    # The set starts with paths already in the database and grows with paths seen in this
    # call, so both already-present and in-run duplicate paths are skipped before batching.
    seen_or_existing_paths = _get_existing_paths_set(
        session=session,
        collection_id=root_collection_id,
        file_paths_abs=normalized_paths,
    )

    samples_to_create: list[ImageCreate] = []
    created_sample_ids: list[UUID] = []

    report = FileOutcomeReport()

    for normalized_path in tqdm(
        normalized_paths,
        desc="Processing images",
        unit=" images",
        disable=not show_progress,
    ):
        with report.track(path=normalized_path):
            # Skip paths already in the database or already seen in this call.
            if normalized_path in seen_or_existing_paths:
                raise AlreadyPresentInputFileError()

            try:
                with fsspec.open(normalized_path, "rb") as file:
                    image = PIL.Image.open(file)
                    width, height = image.size
                    image.close()
            except (FileNotFoundError, PIL.UnidentifiedImageError, OSError):
                continue

            sample = ImageCreate(
                file_name=Path(normalized_path).name,
                file_path_abs=normalized_path,
                width=width,
                height=height,
            )
            seen_or_existing_paths.add(normalized_path)
            samples_to_create.append(sample)

            # Process batch when it reaches SAMPLE_BATCH_SIZE
            if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
                created_path_to_id = _create_batch_samples(
                    session=session, collection_id=root_collection_id, samples=samples_to_create
                )
                created_sample_ids.extend(created_path_to_id.values())
                samples_to_create = []

    # Handle remaining samples
    if samples_to_create:
        created_path_to_id = _create_batch_samples(
            session=session, collection_id=root_collection_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())

    report.log_summary()
    return created_sample_ids


def load_into_dataset_from_labelformat(  # noqa: PLR0913
    session: Session,
    root_collection_id: UUID,
    input_labels: ObjectDetectionInput | InstanceSegmentationInput,
    images_path: PathLike,
    collection_name: str | None = None,
    limit: int | None = None,
) -> list[UUID]:
    """Load samples and their annotations from a labelformat input into the dataset.

    Args:
        session: The database session.
        root_collection_id: The ID of the root collection to load samples into.
        input_labels: The labelformat input containing images and annotations.
        images_path: The path to the directory containing the images.
        collection_name: Optional name for the annotation collection.
        limit: Maximum number of samples to load. By default, all samples are loaded.

    Returns:
        A list of UUIDs of the created samples.
    """
    images_root_abs = add_annotations.normalize_images_root(images_root=images_path)

    # The set starts with paths already in the database and grows with paths seen in this
    # call, so both already-present and in-run duplicate paths are skipped before batching.
    seen_or_existing_paths = _get_existing_paths_set(
        session=session,
        collection_id=root_collection_id,
        file_paths_abs=[
            posixpath.join(images_root_abs, str(image.filename))
            for image in input_labels.get_images()
        ],
    )

    report = FileOutcomeReport()

    samples_to_create: list[ImageCreate] = []
    created_sample_ids: list[UUID] = []

    # Phase 1: Sample creation
    labels: Iterable[object] = input_labels.get_labels()
    if limit is not None:
        labels = itertools.islice(labels, limit)
    for image_data in tqdm(labels, desc="Processing images", unit=" images"):
        image: Image = image_data.image  # type: ignore[attr-defined]

        sample = ImageCreate(
            file_name=str(image.filename),
            file_path_abs=posixpath.join(images_root_abs, str(image.filename)),
            width=image.width,
            height=image.height,
        )

        with report.track(path=sample.file_path_abs):
            # Skip paths already in the database or already seen in this call.
            if sample.file_path_abs in seen_or_existing_paths:
                raise AlreadyPresentInputFileError()

            seen_or_existing_paths.add(sample.file_path_abs)
            samples_to_create.append(sample)

            if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
                created_path_to_id = _create_batch_samples(
                    session=session, collection_id=root_collection_id, samples=samples_to_create
                )
                created_sample_ids.extend(created_path_to_id.values())
                samples_to_create.clear()

    if samples_to_create:
        created_path_to_id = _create_batch_samples(
            session=session, collection_id=root_collection_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())

    # Phase 2: Annotation creation (only if samples were created)
    if created_sample_ids:
        add_annotations.add_annotations_from_labelformat(
            session=session,
            root_collection_id=root_collection_id,
            input_labels=input_labels,
            images_root=images_root_abs,
            collection_name=collection_name,
            restrict_to_sample_ids=set(created_sample_ids),
        )

    report.log_summary()
    return created_sample_ids


def load_into_dataset_from_coco_captions(
    session: Session,
    root_collection_id: UUID,
    annotations_json: Path,
    images_path: Path,
    limit: int | None = None,
) -> list[UUID]:
    """Load samples and captions from a COCO captions file into the dataset.

    Args:
        session: Database session used for resolver operations.
        root_collection_id: Identifier of the root collection that receives the samples.
        annotations_json: Path to the COCO captions annotations file.
        images_path: Directory containing the referenced images.
        limit: Maximum number of samples to load. By default, all samples are loaded.

    Returns:
        The list of newly created sample identifiers.
    """
    with fsspec.open(str(annotations_json), "r") as file:
        coco_payload = json.load(file)

    # A slice with limit=None returns the full list.
    images: list[dict[str, object]] = coco_payload.get("images", [])[:limit]
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

    # The set starts with paths already in the database and grows with paths seen in this
    # call, so both already-present and in-run duplicate paths are skipped before batching.
    seen_or_existing_paths = _get_existing_paths_set(
        session=session,
        collection_id=root_collection_id,
        file_paths_abs=[
            str(images_path / str(image_info["file_name"]))
            for image_info in images
            if isinstance(image_info["id"], int)
        ],
    )

    report = FileOutcomeReport()

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

        with report.track(path=sample.file_path_abs):
            # Skip paths already in the database or already seen in this call.
            if sample.file_path_abs in seen_or_existing_paths:
                raise AlreadyPresentInputFileError()

            seen_or_existing_paths.add(sample.file_path_abs)
            samples_to_create.append(sample)
            path_to_captions[sample.file_path_abs] = captions_by_image_id.get(image_id_raw, [])

            if len(samples_to_create) >= SAMPLE_BATCH_SIZE:
                created_path_to_id = _create_batch_samples(
                    session=session, collection_id=root_collection_id, samples=samples_to_create
                )
                created_sample_ids.extend(created_path_to_id.values())
                _process_batch_captions(
                    session=session,
                    collection_id=root_collection_id,
                    created_path_to_id=created_path_to_id,
                    path_to_captions=path_to_captions,
                )
                samples_to_create.clear()
                path_to_captions.clear()

    if samples_to_create:
        created_path_to_id = _create_batch_samples(
            session=session, collection_id=root_collection_id, samples=samples_to_create
        )
        created_sample_ids.extend(created_path_to_id.values())
        _process_batch_captions(
            session=session,
            collection_id=root_collection_id,
            created_path_to_id=created_path_to_id,
            path_to_captions=path_to_captions,
        )

    report.log_summary()
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

    input_path_abs = add_annotations.normalize_images_root(input_path)

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


def _get_existing_paths_set(
    session: Session, collection_id: UUID, file_paths_abs: Sequence[str]
) -> set[str]:
    """Return the set of file paths that already exist in the collection.

    The database is queried once, up front, so callers can skip already-present paths in
    their main processing loop instead of re-checking the database per batch.

    Args:
        session: The database session.
        collection_id: The ID of the collection to check for existing paths.
        file_paths_abs: The absolute file paths to check.

    Returns:
        The subset of ``file_paths_abs`` that are already present in the collection.
    """
    # Deduplicate before querying so duplicate-heavy inputs don't cause avoidable batching.
    unique_file_paths_abs = list(dict.fromkeys(file_paths_abs))
    _, existing_paths = sample_resolver.filter_new_paths(
        session=session,
        collection_id=collection_id,
        file_paths_abs=unique_file_paths_abs,
    )
    return set(existing_paths)


def _create_batch_samples(
    session: Session, collection_id: UUID, samples: list[ImageCreate]
) -> dict[str, UUID]:
    """Create the batch samples.

    Existence in the database is checked by the caller before the processing loop, so
    this function creates every sample it is given without filtering.

    Args:
        session: The database session.
        collection_id: The ID of the collection to create samples in.
        samples: The samples to create.

    Returns:
        A mapping from file paths to the created sample IDs.
    """
    created_sample_ids = image_resolver.create_many(
        session=session, collection_id=collection_id, samples=samples
    )
    return {
        sample.file_path_abs: sample_id for sample, sample_id in zip(samples, created_sample_ids)
    }


def _process_batch_captions(
    session: Session,
    collection_id: UUID,
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
        session=session, parent_collection_id=collection_id, captions=captions_to_create
    )
