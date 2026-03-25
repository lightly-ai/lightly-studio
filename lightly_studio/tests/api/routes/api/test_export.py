"""Tests for the collection export API routes."""

from __future__ import annotations

import io
import json
import zipfile

from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_OK
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, object_track_resolver, tag_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation_label,
    create_caption,
    create_collection,
    create_image,
    create_images,
    create_tag,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


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
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
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
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
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

    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/annotations",
        params={"annotation_type": "instance_segmentation"},
    )

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

    assert (
        response.headers["Content-Disposition"]
        == "attachment; filename=coco_instance_segmentation_export.json"
    )


def test_export_collection_semantic_segmentations(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img1.jpg",
        width=3,
        height=2,
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
                parent_sample_id=image.sample_id,
                x=1,
                y=0,
                width=1,
                height=1,
                segmentation_mask=[1, 1, 4],
            )
        ],
    )

    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/annotations",
        params={"annotation_type": "semantic_segmentation"},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["Content-Disposition"] == "attachment; filename=pascalvoc.zip"

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        files = set(zip_ref.namelist())
        assert "pascalvoc/class_id_to_name.json" in files
        assert "pascalvoc/SegmentationClass/img1.png" in files

        class_map = json.loads(zip_ref.read("pascalvoc/class_id_to_name.json"))
        assert class_map == {"0": "background", "1": "dog"}

        with PILImage.open(
            io.BytesIO(zip_ref.read("pascalvoc/SegmentationClass/img1.png"))
        ) as mask:
            mask_values = list(mask.getdata())
        assert mask_values == [0, 1, 0, 0, 0, 0]


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


def test_export_collection_youtube_vis(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="video_001.mp4", width=3, height=2, duration_s=2.0, fps=1.0),
    )

    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="cat",
    )
    object_track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=99,
                dataset_id=collection.collection_id,
            )
        ],
    )[0]

    frame_0, _frame_1 = video_with_frames.frame_sample_ids
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=video_with_frames.video_frames_collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=frame_0,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.INSTANCE_SEGMENTATION,
                x=0,
                y=1,
                width=1,
                height=1,
                segmentation_mask=[1, 1, 4],
                object_track_id=object_track_id,
            )
        ],
    )

    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/youtube-vis",
        params={"annotation_type": "instance_segmentation"},
    )

    assert response.status_code == HTTP_STATUS_OK
    content = json.loads(response.content)
    assert content == {
        "info": {"description": "YouTube-VIS export"},
        "categories": [{"id": 1, "name": "cat"}],
        "videos": [
            {
                "id": 1,
                "file_names": ["video_001.mp4/00000.jpg", "video_001.mp4/00001.jpg"],
                "width": 3,
                "height": 2,
                "length": 2,
            }
        ],
        "annotations": [
            {
                "id": 99,
                "video_id": 1,
                "category_id": 1,
                "bboxes": [[0.0, 1.0, 1.0, 1.0], None],
                "segmentations": [
                    {"counts": [2, 1, 3], "size": [2, 3]},
                    None,
                ],
                "areas": [1.0, None],
                "iscrowd": 1,
                "height": 2,
                "width": 3,
                "length": 2,
            }
        ],
    }
    assert (
        response.headers["Content-Disposition"]
        == "attachment; filename=youtube_vis_instance_segmentation_export.json"
    )


def test_export_collection_youtube_vis__wrong_collection_type(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/youtube-vis",
        params={"annotation_type": "instance_segmentation"},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_export_collection_youtube_vis__wrong_annotation_type(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/youtube-vis",
        params={"annotation_type": "object_detection"},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
