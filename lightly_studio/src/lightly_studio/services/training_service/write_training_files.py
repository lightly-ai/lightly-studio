"""Write the input files of a training run."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.dataset import remote_storage
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.services.training_service.training_run_files import TrainingRunFiles

# A low threshold keeps uncertain boxes. They are useful to review and for evaluation.
PREDICTION_SCORE_THRESHOLD = 0.25


def write_training_files(  # noqa: PLR0913
    session: Session,
    collection: CollectionTable,
    files: TrainingRunFiles,
    train_sample_ids: Sequence[UUID],
    val_sample_ids: Sequence[UUID],
    gt_annotation_collection_id: UUID,
    model_name: str,
    steps: int,
) -> None:
    """Write the COCO annotations, the images to predict on and the config of a run.

    Raises:
        ValueError: If the train samples have no ground truth annotations, or if an image
            is not on the local disk.
    """
    files.run_dir.mkdir(parents=True)
    for sample_ids, output_file in (
        (train_sample_ids, files.train_annotations_file),
        (val_sample_ids, files.val_annotations_file),
    ):
        _export_coco(
            session=session,
            collection=collection,
            sample_ids=sample_ids,
            annotation_collection_id=gt_annotation_collection_id,
            output_file=output_file,
        )
    if _annotation_count(coco_file=files.train_annotations_file) == 0:
        raise ValueError("The train samples have no annotations in the ground truth source.")

    _write_predict_images(session=session, collection=collection, files=files)
    config = {
        "model_name": model_name,
        "steps": steps,
        "score_threshold": PREDICTION_SCORE_THRESHOLD,
        "train_annotations_file": str(files.train_annotations_file),
        "val_annotations_file": str(files.val_annotations_file),
        "predict_images_file": str(files.predict_images_file),
        "predictions_file": str(files.predictions_file),
        "stage_file": str(files.stage_file),
        "out_dir": str(files.out_dir),
    }
    files.config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _export_coco(
    session: Session,
    collection: CollectionTable,
    sample_ids: Sequence[UUID],
    annotation_collection_id: UUID,
    output_file: Path,
) -> None:
    image_filter = ImageFilter(sample_filter=SampleFilter(sample_ids=list(sample_ids)))
    query = DatasetQuery(dataset=collection, session=session).filter_by_sample_ids(
        image_filter.build_sample_ids_query(collection_id=collection.collection_id)
    )
    ImageDatasetExport(
        session=session, dataset_id=collection.dataset_id, samples=query
    ).to_coco_object_detections(
        output_json=output_file, annotation_collection_id=annotation_collection_id
    )


def _annotation_count(coco_file: Path) -> int:
    return len(json.loads(coco_file.read_text(encoding="utf-8"))["annotations"])


def _write_predict_images(
    session: Session, collection: CollectionTable, files: TrainingRunFiles
) -> None:
    images = image_resolver.get_all_by_collection_id(
        session=session, collection_id=collection.collection_id
    ).samples
    remote_paths = [i.file_path_abs for i in images if remote_storage.is_remote(i.file_path_abs)]
    if remote_paths:
        raise ValueError(
            f"Training needs images on the local disk. {len(remote_paths)} images are "
            f"remote, for example '{remote_paths[0]}'."
        )
    entries = [{"sample_id": str(i.sample_id), "path": i.file_path_abs} for i in images]
    files.predict_images_file.write_text(json.dumps(entries), encoding="utf-8")
