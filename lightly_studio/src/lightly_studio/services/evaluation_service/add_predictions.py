"""Load COCO-format predictions into the DB as a named AnnotationCollection."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_collection import AnnotationCollectionTable
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import annotation_collection_resolver, annotation_label_resolver
from lightly_studio.resolvers.annotation_resolver import create_many
from lightly_studio.resolvers.collection_resolver import get_or_create_child_collection
from lightly_studio.models.collection import SampleType

logger = logging.getLogger(__name__)


def add_predictions_from_coco(
    session: Session,
    dataset_id: UUID,
    root_collection_id: UUID,
    gt_annotations_json: Path,
    predictions_json: Path,
    collection_name: str,
) -> AnnotationCollectionTable:
    """Load COCO-format predictions and register them as a named AnnotationCollection.

    Args:
        gt_annotations_json: Standard COCO annotations JSON. Used only for the
            image_id → file_name and category_id → category_name mappings.
        predictions_json: COCO results JSON — a list of dicts with keys
            image_id, category_id, bbox ([x, y, w, h]), score.
        collection_name: Name for the new AnnotationCollection (e.g. "YOLOv8-n epoch 50").
    """
    existing = annotation_collection_resolver.get_by_name(
        session=session, dataset_id=dataset_id, name=collection_name
    )
    if existing is not None:
        logger.warning(
            "Annotation collection '%s' already exists — skipping import.", collection_name
        )
        return existing

    with open(gt_annotations_json) as f:
        gt_data = json.load(f)

    with open(predictions_json) as f:
        raw_preds = json.load(f)

    # Build helper maps from GT JSON
    image_id_to_filename: dict[int, str] = {
        img["id"]: img["file_name"] for img in gt_data.get("images", [])
    }
    cat_id_to_name: dict[int, str] = {
        cat["id"]: cat["name"] for cat in gt_data.get("categories", [])
    }

    # Resolve file_name → sample UUID via DB
    all_filenames = set(image_id_to_filename.values())
    stmt = select(ImageTable).where(col(ImageTable.file_name).in_(list(all_filenames)))
    filename_to_sample_id: dict[str, UUID] = {
        img.file_name: img.sample_id for img in session.exec(stmt).all()
    }

    # Resolve category_name → annotation_label UUID (create if missing)
    cat_name_to_label_id: dict[str, UUID] = {}
    for cat_name in set(cat_id_to_name.values()):
        label = annotation_label_resolver.get_by_label_name(
            session=session, dataset_id=dataset_id, label_name=cat_name
        )
        if label is None:
            label = annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=dataset_id, annotation_label_name=cat_name
                ),
            )
        cat_name_to_label_id[cat_name] = label.annotation_label_id

    # Build AnnotationCreate objects
    annotations: list[AnnotationCreate] = []
    skipped = 0
    for pred in raw_preds:
        file_name = image_id_to_filename.get(pred["image_id"])
        if file_name is None:
            skipped += 1
            continue
        parent_sample_id = filename_to_sample_id.get(file_name)
        if parent_sample_id is None:
            skipped += 1
            continue
        cat_name = cat_id_to_name.get(pred["category_id"])
        if cat_name is None:
            skipped += 1
            continue

        x, y, w, h = (int(v) for v in pred["bbox"])
        annotations.append(
            AnnotationCreate(
                annotation_label_id=cat_name_to_label_id[cat_name],
                annotation_type=AnnotationType.OBJECT_DETECTION,
                confidence=float(pred.get("score", 0.0)),
                parent_sample_id=parent_sample_id,
                x=x,
                y=y,
                width=w,
                height=h,
            )
        )

    if skipped:
        logger.warning("Skipped %d predictions (unresolved image_id or category_id).", skipped)

    # get_or_create_child_collection is called internally by create_many, so we call it
    # first to obtain the annotation child collection UUID for AnnotationCollectionTable.
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
