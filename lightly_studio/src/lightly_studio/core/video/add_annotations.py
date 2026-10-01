"""Functions to add annotations to videos already present in a dataset."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from labelformat.formats import ActivityNetTemporalClassificationInput
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core import labelformat_helpers
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.resolvers import (
    annotation_resolver,
    video_resolver,
)
from lightly_studio.type_definitions import PathLike

logger = logging.getLogger(__name__)

ANNOTATION_BATCH_SIZE = 1024


def add_annotations_from_activitynet(
    session: Session,
    root_collection_id: UUID,
    annotations_json: PathLike,
    collection_name: str | None = None,
) -> list[str]:
    """Add ActivityNet-style event annotations to videos already in a collection.

    Args:
        session: The database session.
        root_collection_id: The ID of the root video collection.
        annotations_json: Path to an ActivityNet-style JSON file.
        collection_name: Optional name for the annotation source. If ``None``, a default
            name is used.

    Returns:
        A list of video IDs from the JSON that had no matching video in the collection.
    """
    annotations_json = Path(annotations_json).absolute()
    if not annotations_json.is_file() or annotations_json.suffix != ".json":
        raise FileNotFoundError(
            f"ActivityNet annotations json file not found: '{annotations_json}'"
        )

    input_labels = ActivityNetTemporalClassificationInput(input_file=annotations_json)
    stem_to_sample_id = video_resolver.get_sample_ids_by_stems(
        session=session,
        collection_id=root_collection_id,
    )
    label_map = labelformat_helpers.create_label_map(
        session=session,
        root_collection_id=root_collection_id,
        input_labels=input_labels,
    )

    missing_video_ids: list[str] = []
    annotations_to_create: list[AnnotationCreate] = []

    for video_label in tqdm(
        input_labels.get_labels(), desc="Processing ActivityNet annotations", unit=" videos"
    ):
        video_sample_id = stem_to_sample_id.get(video_label.video_id)
        if video_sample_id is None:
            missing_video_ids.append(video_label.video_id)
            continue

        for event in video_label.events:
            annotations_to_create.append(
                AnnotationCreate(
                    annotation_label_id=label_map[event.category.id],
                    annotation_type=AnnotationType.CLASSIFICATION,
                    confidence=event.confidence,
                    parent_sample_id=video_sample_id,
                    start_time_s=event.start_time_s,
                    end_time_s=event.end_time_s,
                )
            )

            if len(annotations_to_create) >= ANNOTATION_BATCH_SIZE:
                annotation_resolver.create_many(
                    session=session,
                    parent_collection_id=root_collection_id,
                    annotations=annotations_to_create,
                    collection_name=collection_name,
                )
                annotations_to_create.clear()

    if annotations_to_create:
        annotation_resolver.create_many(
            session=session,
            parent_collection_id=root_collection_id,
            annotations=annotations_to_create,
            collection_name=collection_name,
        )

    if missing_video_ids:
        logger.warning(
            "Skipped %d ActivityNet video IDs with no matching video in the collection.",
            len(missing_video_ids),
        )

    return missing_video_ids
