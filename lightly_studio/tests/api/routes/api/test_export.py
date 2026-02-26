"""Tests for the collection export API routes."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_OK,
)
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver, tag_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation_label,
    create_caption,
    create_collection,
    create_image,
    create_images,
    create_tag,
)


def test_export_collection_annotations(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # Create a single sample with a single annotation.
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img1.jpg",
        width=100,
        height=100,
    )
    label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="cat"
    )
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                parent_sample_id=image.sample_id,
                x=10,
                y=20,
                width=30,
                height=40,
            )
        ],
    )

    # Call the API.
    response = test_client.get(f"/api/collections/{collection.collection_id}/export/annotations")

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


def test_export_collection_captions(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # Create a single sample with a single annotation.
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img1.jpg",
        width=100,
        height=100,
    )
    create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=image.sample_id,
        text="test caption",
    )

    # Call the API.
    response = test_client.get(f"/api/collections/{collection.collection_id}/export/captions")

    # Check the response.
    assert response.status_code == HTTP_STATUS_OK
    content = json.loads(response.content)
    assert content == {
        "images": [{"id": 0, "file_name": "img1.jpg", "width": 100, "height": 100}],
        "annotations": [{"id": 0, "image_id": 0, "caption": "test caption"}],
    }

    # Check the export file name. Quotes are intentionally omitted.
    assert (
        response.headers["Content-Disposition"] == "attachment; filename=coco_captions_export.json"
    )


def test_export_collection_samples(db_session: Session, test_client: TestClient) -> None:
    client = test_client
    collection_id = create_collection(
        session=db_session, collection_name="example_collection"
    ).collection_id
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="path/to/image0.jpg"),
            ImageStub(path="path/to/image1.jpg"),
            ImageStub(path="path/to/image2.jpg"),
        ],
    )

    # Tag two samples.
    tag = create_tag(session=db_session, collection_id=collection_id)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=images[0].sample)
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=images[2].sample)

    # Export the collection
    response = client.post(
        f"/api/collections/{collection_id}/export",
        json={"include": {"tag_ids": [str(tag.tag_id)]}},
    )
    assert response.status_code == HTTP_STATUS_OK

    lines = response.text.split("\n")
    assert lines == ["path/to/image0.jpg", "path/to/image2.jpg"]


def test_export_collection_instance_segmentations(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # Create a single sample with a single annotation.
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img1.jpg",
        width=10,
        height=10,
    )
    label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="cat"
    )
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
                parent_sample_id=image.sample_id,
                x=2,
                y=0,
                width=3,
                height=2,
                segmentation_mask=[2, 3, 7, 2, 86],
            )
        ],
    )

    # Call the API.
    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/instance-segmentations"
    )

    # Check the response.
    assert response.status_code == HTTP_STATUS_OK
    content = json.loads(response.content)

    assert content == {
        "images": [{"id": 0, "file_name": "img1.jpg", "width": 10, "height": 10}],
        "categories": [{"id": 0, "name": "cat"}],
        "annotations": [
            {
                "image_id": 0,
                "category_id": 0,
                "segmentation": {"counts": [20, 2, 8, 2, 8, 1, 59], "size": [10, 10]},
                "bbox": [2.0, 0.0, 3.0, 2.0],
                "iscrowd": 1,
            }
        ],
    }

    # Check the export file name.
    assert (
        response.headers["Content-Disposition"]
        == "attachment; filename=coco_instance_segmentation_export.json"
    )
