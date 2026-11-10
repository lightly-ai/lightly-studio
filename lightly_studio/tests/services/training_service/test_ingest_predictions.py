from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session

from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver
from lightly_studio.services.training_service import ingest_predictions
from tests.services.training_service import helpers


def test_ingest_predictions(db_session: Session, tmp_path: Path) -> None:
    dataset = helpers.create_training_dataset(session=db_session)
    image = dataset.images[2]
    predictions_file = tmp_path / "predictions.json"
    detections = [
        {"class_name": "cat", "bbox_xyxy": [10.4, 20.6, 50.4, 60.6], "score": 0.5},
        {"class_name": "dog", "bbox_xyxy": [0.0, 0.0, 5.0, 8.0], "score": 0.25},
        # A box with no area is skipped.
        {"class_name": "cat", "bbox_xyxy": [5.0, 5.0, 5.2, 9.0], "score": 0.8},
    ]
    predictions_file.write_text(
        json.dumps([{"sample_id": str(image.sample_id), "detections": detections}])
    )

    count = ingest_predictions.ingest_predictions(
        session=db_session,
        collection_id=dataset.collection.collection_id,
        dataset_id=dataset.collection.dataset_id,
        predictions_file=predictions_file,
        annotation_source="run_1",
    )

    assert count == 2
    annotations = annotation_resolver.get_all_by_collection_name(
        session=db_session,
        parent_collection_id=dataset.collection.collection_id,
        collection_name="run_1",
    ).annotations
    boxes = sorted(
        (
            a.annotation_label.annotation_label_name,
            a.object_detection_details.x,
            a.object_detection_details.y,
            a.object_detection_details.width,
            a.object_detection_details.height,
            a.confidence,
        )
        for a in annotations
        if a.object_detection_details is not None
    )
    assert boxes == [("cat", 10, 21, 40, 40, 0.5), ("dog", 0, 0, 5, 8, 0.25)]
    assert all(a.parent_sample_id == image.sample_id for a in annotations)
    assert (
        annotation_label_resolver.get_by_label_name(
            session=db_session, dataset_id=dataset.collection.dataset_id, label_name="dog"
        )
        is not None
    )
