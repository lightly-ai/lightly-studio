"""Move data between the LightlyStudio dataset and LightlyTrain.

Two directions:

- `export_training_data` writes the annotations of the current grid view as COCO files
  that LightlyTrain trains on.
- `predict_and_evaluate` writes the predictions of a trained model back as a separate
  annotation source and creates an evaluation run, so the confusion matrix and the
  per-image true/false positives show up in the LightlyStudio Eval tab.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import lightly_train  # type: ignore[import-not-found]
from PIL import Image
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.database import db_manager
from lightly_studio.evaluation.image_dataset_evaluate import (
    ImageDatasetEvaluate,
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.export import image_dataset_export
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    image_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter

logger = logging.getLogger(__name__)

_MIN_IMAGES_PER_SPLIT = 1
_SPLIT_SEED = 0


@dataclass(frozen=True)
class ExportRequest:
    """What to export for a training run.

    Attributes:
        collection_id: Root collection of the dataset.
        image_filter: Filter of the current grid view, or None for the whole collection.
        annotation_source: Name of the annotation source holding the ground truth.
        val_fraction: Share of labeled images used for validation.
        output_dir: Directory that receives `train.json` and `val.json`.
    """

    collection_id: UUID
    image_filter: ImageFilter | None
    annotation_source: str
    val_fraction: float
    output_dir: Path


@dataclass(frozen=True)
class PrelabelRequest:
    """What to pre-label and with which model.

    Attributes:
        collection_id: Root collection of the dataset.
        image_filter: Filter of the current grid view, or None for the whole collection.
        model: LightlyTrain model name or path to an exported checkpoint.
        annotation_source: Annotation source that receives the boxes. Use the source that
            the user labels in, so that the boxes are there to correct.
        score_threshold: Minimum score for a box to be written.
        class_map: Model class name to annotation class name. An empty map keeps every
            class of the model under its own name.
        device: Device the model runs on.
    """

    collection_id: UUID
    image_filter: ImageFilter | None
    model: str
    annotation_source: str
    score_threshold: float
    class_map: dict[str, str]
    device: str


@dataclass(frozen=True)
class EvaluationRequest:
    """What to predict on and how to name the resulting evaluation run.

    Attributes:
        collection_id: Root collection of the dataset.
        checkpoint: Exported LightlyTrain model.
        sample_ids: Image samples to predict on, usually the validation split.
        prediction_source: Annotation source that receives the predictions.
        ground_truth_source: Annotation source holding the human annotations.
        evaluation_name: Name of the evaluation run.
        score_threshold: Minimum score for a prediction to be written.
        device: Device the model runs on.
    """

    collection_id: UUID
    checkpoint: Path
    sample_ids: list[UUID]
    prediction_source: str
    ground_truth_source: str
    evaluation_name: str
    score_threshold: float
    device: str


@dataclass(frozen=True)
class TrainingDataExport:
    """Result of exporting the labeled images of a view.

    Attributes:
        train_sample_ids: Sample IDs in the train split.
        val_sample_ids: Sample IDs in the validation split.
        class_names: Annotation classes in the exported annotations.
        labeled_count: Number of images that carry at least one annotation.
        skipped_count: Number of images in the view without annotations.
    """

    train_sample_ids: list[UUID]
    val_sample_ids: list[UUID]
    class_names: list[str]
    labeled_count: int
    skipped_count: int


class TrainedModelEvaluationConfig(ObjectDetectionEvaluationConfig):
    """Evaluation config that also carries the training settings of the run.

    LightlyStudio shows every field of the config in the evaluation run panel, so the
    training settings and the LightlyTrain validation metrics appear next to the
    confusion matrix.
    """

    model: str = ""
    training_steps: int = 0
    train_images: int = 0
    val_images: int = 0
    lightly_train_map_50: float = 0.0
    lightly_train_map: float = 0.0
    score_threshold: float = 0.0


def export_training_data(session: Session, request: ExportRequest) -> TrainingDataExport:
    """Write train and validation COCO files for the labeled images of a view.

    Images without annotations in `annotation_source` are left out: LightlyTrain
    treats an image with no boxes as a negative example, which is not what a
    half-labeled dataset means.

    Args:
        session: Database session.
        request: What to export and where to write it.

    Returns:
        A summary of the export.

    Raises:
        ValueError: If the view holds fewer than two labeled images.
    """
    collection_id = request.collection_id
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection {collection_id} does not exist.")
    source_id = collection_resolver.get_by_name(
        session=session, name=request.annotation_source, parent_collection_id=collection_id
    )
    if source_id is None:
        raise ValueError(
            f"Annotation source '{request.annotation_source}' does not exist. "
            "Label some images first."
        )

    query = DatasetQuery(dataset=collection, session=session)
    if request.image_filter is not None:
        query.filter_by_sample_ids(request.image_filter.build_sample_ids_query(collection_id))
    exporter = image_dataset_export.ImageDatasetExport(
        session=session, dataset_id=collection.dataset_id, samples=query
    )
    request.output_dir.mkdir(parents=True, exist_ok=True)
    full_export = request.output_dir / "all.json"
    exporter.to_coco_object_detections(output_json=full_export, annotation_collection_id=source_id)

    coco = json.loads(full_export.read_text())
    labeled_image_ids = {annotation["image_id"] for annotation in coco["annotations"]}
    labeled_images = [image for image in coco["images"] if image["id"] in labeled_image_ids]
    skipped_count = len(coco["images"]) - len(labeled_images)
    if len(labeled_images) < 2 * _MIN_IMAGES_PER_SPLIT:
        raise ValueError(
            f"Need at least {2 * _MIN_IMAGES_PER_SPLIT} labeled images, "
            f"found {len(labeled_images)}. Draw bounding boxes on more images."
        )

    shuffled = sorted(labeled_images, key=lambda image: image["file_name"])
    random.Random(_SPLIT_SEED).shuffle(shuffled)
    val_count = min(
        max(_MIN_IMAGES_PER_SPLIT, round(len(shuffled) * request.val_fraction)),
        len(shuffled) - _MIN_IMAGES_PER_SPLIT,
    )
    val_images = shuffled[:val_count]
    train_images = shuffled[val_count:]
    _write_split(coco=coco, images=train_images, path=request.output_dir / "train.json")
    _write_split(coco=coco, images=val_images, path=request.output_dir / "val.json")

    path_to_sample_id = _path_to_sample_id(
        session=session, collection_id=collection_id, image_filter=request.image_filter
    )
    return TrainingDataExport(
        train_sample_ids=_sample_ids(images=train_images, path_to_sample_id=path_to_sample_id),
        val_sample_ids=_sample_ids(images=val_images, path_to_sample_id=path_to_sample_id),
        class_names=[category["name"] for category in coco["categories"]],
        labeled_count=len(labeled_images),
        skipped_count=skipped_count,
    )


def predict_and_evaluate(request: EvaluationRequest, config: TrainedModelEvaluationConfig) -> str:
    """Predict on the validation images and create a LightlyStudio evaluation run.

    Runs in the background after training, with its own database session.

    Args:
        request: Model, samples and annotation sources of the evaluation.
        config: Evaluation config, including the training settings shown in the UI.

    Returns:
        A short summary for the UI.
    """
    collection_id = request.collection_id
    model = lightly_train.load_model(model=str(request.checkpoint), device=request.device)
    class_names: dict[int, str] = dict(model.classes)

    with db_manager.session() as session:
        samples = image_resolver.get_many_by_id(session=session, sample_ids=request.sample_ids)
        label_map = _get_or_create_labels(
            session=session, collection_id=collection_id, class_names=class_names
        )
        annotations: list[AnnotationCreate] = []
        for sample in samples:
            with Image.open(sample.file_path_abs) as opened:
                prediction = model.predict(opened.convert("RGB"), threshold=request.score_threshold)
            for label, box, score in zip(
                prediction["labels"].tolist(),
                prediction["bboxes"].tolist(),
                prediction["scores"].tolist(),
            ):
                label_id = label_map.get(int(label))
                if label_id is None:
                    continue
                x1, y1, x2, y2 = (round(value) for value in box)
                annotations.append(
                    AnnotationCreate(
                        annotation_label_id=label_id,
                        annotation_type=AnnotationType.OBJECT_DETECTION,
                        parent_sample_id=sample.sample_id,
                        x=max(0, x1),
                        y=max(0, y1),
                        width=max(0, x2 - x1),
                        height=max(0, y2 - y1),
                        confidence=round(float(score), 3),
                    )
                )
        annotation_resolver.create_many(
            session=session,
            parent_collection_id=collection_id,
            annotations=annotations,
            collection_name=request.prediction_source,
        )
        # Cover every validation image, also the ones the model found nothing in.
        # Without this, those images would silently drop out of the evaluation.
        source_id = collection_resolver.get_by_name(
            session=session, name=request.prediction_source, parent_collection_id=collection_id
        )
        if source_id is not None:
            annotation_collection_coverage_resolver.add_many(
                session=session,
                annotation_collection_id=source_id,
                parent_sample_ids=request.sample_ids,
            )

        result = ImageDatasetEvaluate(
            session=session, collection_id=collection_id, sample_ids=request.sample_ids
        ).object_detection(
            name=request.evaluation_name,
            gt_annotation_source=request.ground_truth_source,
            pred_annotation_source=request.prediction_source,
            config=config,
        )
    logger.info("Created evaluation run %s.", request.evaluation_name)
    return (
        f"{len(annotations)} predictions on {result.sample_count} validation images. "
        f"See the Eval tab for '{request.evaluation_name}'."
    )


def prelabel_images(session: Session, request: PrelabelRequest) -> tuple[int, int, list[str]]:
    """Write model boxes into the annotation source that the user labels in.

    The boxes are normal annotations, so the user can move them, correct the class, or
    delete them. Images that already hold annotations in that source stay untouched: a
    frame that a person labeled must not get a second set of boxes.

    Args:
        session: Database session.
        request: Model, view and class names of the pre-labeling.

    Returns:
        The number of boxes written, the number of images that got boxes, and the
        class names that were used.
    """
    model = lightly_train.load_model(model=str(request.model), device=request.device)
    model_classes: dict[int, str] = dict(model.classes)
    class_names: dict[int, str] = {
        class_id: request.class_map.get(name) or name
        for class_id, name in model_classes.items()
        if not request.class_map or name in request.class_map
    }
    if not class_names:
        raise ValueError(
            f"The model knows none of these classes: {', '.join(sorted(request.class_map))}. "
            f"It knows: {', '.join(sorted(model_classes.values())[:12])}."
        )

    result = image_resolver.get_all_by_collection_id(
        session=session, collection_id=request.collection_id, filters=request.image_filter
    )
    samples = list(result.samples)
    source_id = collection_resolver.get_by_name(
        session=session, name=request.annotation_source, parent_collection_id=request.collection_id
    )
    already_labeled = _samples_with_annotations(
        session=session, samples=samples, annotation_collection_id=source_id
    )
    label_map = _get_or_create_labels(
        session=session, collection_id=request.collection_id, class_names=class_names
    )
    annotations: list[AnnotationCreate] = []
    image_count = 0
    for sample in samples:
        if sample.sample_id in already_labeled:
            continue
        with Image.open(sample.file_path_abs) as opened:
            prediction = model.predict(opened.convert("RGB"), threshold=request.score_threshold)
        boxes_before = len(annotations)
        for label, box, score in zip(
            prediction["labels"].tolist(),
            prediction["bboxes"].tolist(),
            prediction["scores"].tolist(),
        ):
            label_id = label_map.get(int(label))
            if label_id is None:
                continue
            x1, y1, x2, y2 = (round(value) for value in box)
            annotations.append(
                AnnotationCreate(
                    annotation_label_id=label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    parent_sample_id=sample.sample_id,
                    x=max(0, x1),
                    y=max(0, y1),
                    width=max(0, x2 - x1),
                    height=max(0, y2 - y1),
                    confidence=round(float(score), 3),
                )
            )
        image_count += 1 if len(annotations) > boxes_before else 0
    if annotations:
        annotation_resolver.create_many(
            session=session,
            parent_collection_id=request.collection_id,
            annotations=annotations,
            collection_name=request.annotation_source,
        )
    return len(annotations), image_count, sorted(set(class_names.values()))


def _samples_with_annotations(
    session: Session, samples: list[Any], annotation_collection_id: UUID | None
) -> set[UUID]:
    if annotation_collection_id is None or not samples:
        return set()
    existing = annotation_resolver.get_all_by_parent_sample_ids_and_annotation_collection_id(
        session=session,
        parent_sample_ids=[sample.sample_id for sample in samples],
        annotation_collection_id=annotation_collection_id,
    )
    return {annotation.parent_sample_id for annotation in existing}


def _write_split(coco: dict[str, Any], images: list[dict[str, Any]], path: Path) -> None:
    image_ids = {image["id"] for image in images}
    split = {
        "images": images,
        "annotations": [a for a in coco["annotations"] if a["image_id"] in image_ids],
        "categories": coco["categories"],
    }
    path.write_text(json.dumps(split))


def _path_to_sample_id(
    session: Session, collection_id: UUID, image_filter: ImageFilter | None
) -> dict[str, UUID]:
    result = image_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id, filters=image_filter
    )
    return {sample.file_path_abs: sample.sample_id for sample in result.samples}


def _sample_ids(images: list[dict[str, Any]], path_to_sample_id: dict[str, UUID]) -> list[UUID]:
    # The COCO export writes absolute file paths, which identify the sample.
    return [
        path_to_sample_id[image["file_name"]]
        for image in images
        if image["file_name"] in path_to_sample_id
    ]


def _get_or_create_labels(
    session: Session, collection_id: UUID, class_names: dict[int, str]
) -> dict[int, UUID]:
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection {collection_id} does not exist.")
    label_map: dict[int, UUID] = {}
    for class_id, class_name in class_names.items():
        label = annotation_label_resolver.get_by_label_name(
            session=session, dataset_id=collection.dataset_id, label_name=class_name
        )
        if label is None:
            label = annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=collection.dataset_id, annotation_label_name=class_name
                ),
            )
        label_map[class_id] = label.annotation_label_id
    return label_map
