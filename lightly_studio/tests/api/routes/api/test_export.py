"""Tests for the dataset export API routes."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.resolvers import annotation_resolver
from tests.helpers_resolvers import (
    create_annotation_label,
    create_dataset,
    create_image,
)


def test_export_dataset_annotations(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # Create a single sample with a single annotation.
    dataset = create_dataset(session=db_session)
    image = create_image(
        session=db_session,
        dataset_id=dataset.dataset_id,
        file_path_abs="img1.jpg",
        width=100,
        height=100,
    )
    label = create_annotation_label(session=db_session, annotation_label_name="cat")
    annotation_resolver.create_many(
        session=db_session,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                dataset_id=dataset.dataset_id,
                parent_sample_id=image.sample_id,
                x=10,
                y=20,
                width=30,
                height=40,
            )
        ],
    )

    # Call the API.
    response = test_client.get(f"/api/datasets/{dataset.dataset_id}/export/annotations")

    # Check the response.
    assert response.status_code == HTTP_STATUS_OK
    content = json.loads(response.content)
    assert content == {
        "images": [{"id": 0, "file_name": "img1.jpg", "width": 100, "height": 100}],
        "categories": [{"id": 0, "name": "cat"}],
        "annotations": [{"image_id": 0, "category_id": 0, "bbox": [10.0, 20.0, 30.0, 40.0]}],
    }

    # Check the export file name. Quotes are intentionally omitted.
    assert response.headers["Content-Disposition"] == "attachment; filename=coco_export.json"
