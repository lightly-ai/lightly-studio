"""Tests for the collection export API routes."""

from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from pathlib import Path
from unittest import mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api import export as export_api
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.models.export_job import ExportJobTable
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    export_job_resolver,
    object_track_resolver,
)
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_caption,
    create_collection,
    create_image,
)
from tests.resolvers.video.helpers import VideoStub, create_video, create_video_with_frames


def test_export_collection_prepare(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session, collection_name="my_collection")
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="path/a.png",
    )
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="path/b.png",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/prepare",
        json={},
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    file_content = Path(export_job.export_path).read_text()
    assert set(file_content.splitlines()) == {"path/a.png", "path/b.png"}


def test_export_collection_prepare__with_collection_filter(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="path/a.png",
    )
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="path/b.png",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/prepare",
        json={
            "collection_filter": {
                "filter_type": "image",
                "sample_filter": {"sample_ids": [str(image_a.sample_id)]},
            }
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    assert Path(export_job.export_path).read_text() == "path/a.png"


def test_export_download__not_found_returns_404(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    export_key = uuid4()

    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/download/{export_key}"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_export_download__wrong_collection_returns_404(
    tmp_path: Path,
    db_session: Session,
    test_client: TestClient,
) -> None:
    owning_collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)

    export_path = tmp_path / "export.json"
    export_path.write_text('{"items": [1, 2, 3]}')
    job = export_job_resolver.create(
        session=db_session,
        collection_id=owning_collection.collection_id,
        export_path=str(export_path),
    )

    response = test_client.get(
        f"/api/collections/{other_collection.collection_id}/export/download/{job.export_key}"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert export_job_resolver.get(session=db_session, export_key=job.export_key) is not None
    assert export_path.exists()


def test_export_download__json_file_streams_content_and_deletes_job(
    tmp_path: Path,
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)

    export_dir = tmp_path / "container"
    export_dir.mkdir()
    export_path = export_dir / "export.json"
    export_path.write_text('{"items": [1, 2, 3]}')

    job = export_job_resolver.create(
        session=db_session, collection_id=collection.collection_id, export_path=str(export_path)
    )

    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/download/{job.export_key}"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["Content-Disposition"] == "attachment; filename=export.json"
    assert response.json() == {"items": [1, 2, 3]}
    assert export_job_resolver.get(session=db_session, export_key=job.export_key) is None
    assert not export_path.exists()
    assert export_dir.exists()


def test_export_download__txt_file_streams_content_and_deletes_job(
    tmp_path: Path,
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)

    export_dir = tmp_path / "container"
    export_dir.mkdir()
    export_path = export_dir / "export.txt"
    export_path.write_text("path/a.jpg\npath/b.jpg\n")

    job = export_job_resolver.create(
        session=db_session, collection_id=collection.collection_id, export_path=str(export_path)
    )

    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/download/{job.export_key}"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["Content-Type"].startswith("text/plain")
    assert response.headers["Content-Disposition"] == "attachment; filename=export.txt"
    assert response.text == "path/a.jpg\npath/b.jpg\n"
    assert export_job_resolver.get(session=db_session, export_key=job.export_key) is None
    assert not export_path.exists()
    assert export_dir.exists()


def test_export_download__csv_file_streams_content_and_deletes_job(
    tmp_path: Path,
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    export_dir = tmp_path / "container"
    export_dir.mkdir()
    export_path = export_dir / "classification_export.csv"
    export_path.write_text("file_path_abs,class_name\n/data/img1.jpg,cat\n")
    job = export_job_resolver.create(
        session=db_session, collection_id=collection.collection_id, export_path=str(export_path)
    )

    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/download/{job.export_key}"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["Content-Type"].startswith("text/csv")
    assert response.headers["Content-Disposition"] == (
        "attachment; filename=classification_export.csv"
    )
    assert response.text == "file_path_abs,class_name\n/data/img1.jpg,cat\n"
    assert export_job_resolver.get(session=db_session, export_key=job.export_key) is None
    assert not export_path.exists()
    assert export_dir.exists()


def test_export_download__directory_streams_as_zip_and_deletes_job(
    tmp_path: Path,
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)

    container = tmp_path / "container"
    container.mkdir()
    export_dir = container / "my_export"
    export_dir.mkdir()
    (export_dir / "labels.txt").write_text("cat\ndog\n")

    job = export_job_resolver.create(
        session=db_session, collection_id=collection.collection_id, export_path=str(export_dir)
    )

    response = test_client.get(
        f"/api/collections/{collection.collection_id}/export/download/{job.export_key}"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["Content-Type"] == "application/zip"
    assert response.headers["Content-Disposition"] == "attachment; filename=my_export.zip"

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        assert "my_export/labels.txt" in zip_ref.namelist()
        assert zip_ref.read("my_export/labels.txt") == b"cat\ndog\n"

    assert export_job_resolver.get(session=db_session, export_key=job.export_key) is None
    assert not export_dir.exists()
    assert container.exists()


def test_export_collection_annotations_prepare__coco(
    db_session: Session,
    test_client: TestClient,
) -> None:
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
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/annotations/prepare",
        json={
            "export_format": "object_detection_coco",
            "annotation_collection_id": str(annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    content = json.loads(Path(export_job.export_path).read_text())
    assert content == {
        "images": [{"id": 0, "file_name": "img1.jpg", "width": 100, "height": 100}],
        "categories": [{"id": 0, "name": "cat"}],
        "annotations": [{"image_id": 0, "category_id": 0, "bbox": [10.0, 20.0, 30.0, 40.0]}],
    }


def test_export_collection_annotations_prepare__classification_csv(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/data/img1.jpg",
    )
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                confidence=0.5,
            )
        ],
        collection_name="model",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/annotations/prepare",
        json={
            "export_format": "classification_csv",
            "annotation_collection_id": str(annotations[0].annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_job = db_session.get(ExportJobTable, UUID(response.json()["export_key"]))
    assert export_job is not None
    export_path = Path(export_job.export_path)
    assert export_path.name == "classification_export.csv"
    assert list(csv.DictReader(io.StringIO(export_path.read_text()))) == [
        {
            "file_path_abs": "/data/img1.jpg",
            "class_name": "cat",
            "confidence": "0.5",
            "annotation_source": "model",
        }
    ]


def test_export_collection_annotations_prepare__video_classification_filter(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    included = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/included.mp4"),
    )
    excluded = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/excluded.mp4"),
    )
    label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="cat",
    )
    selected = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
            for sample_id in (included.sample_id, excluded.sample_id)
        ],
        collection_name="selected",
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=included.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
        ],
        collection_name="excluded-source",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/annotations/prepare",
        json={
            "export_format": "classification_csv",
            "annotation_collection_id": str(selected[0].annotation_collection_id),
            "video_filter": {
                "filter_type": "video",
                "sample_filter": {"sample_ids": [str(included.sample_id)]},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_job = db_session.get(ExportJobTable, UUID(response.json()["export_key"]))
    assert export_job is not None
    assert list(csv.DictReader(io.StringIO(Path(export_job.export_path).read_text()))) == [
        {
            "file_path_abs": "/data/included.mp4",
            "class_name": "cat",
            "confidence": "",
            "annotation_source": "selected",
        }
    ]


def test_export_collection_annotations_prepare__yolo(
    db_session: Session,
    test_client: TestClient,
) -> None:
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
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/annotations/prepare",
        json={
            "export_format": "object_detection_yolo",
            "annotation_collection_id": str(annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    export_dir = Path(export_job.export_path)
    assert (export_dir / "data.yaml").exists()
    assert (export_dir / "labels" / "img1.txt").exists()


def test_export_collection_annotations_prepare__segmentation_mask_coco(
    db_session: Session,
    test_client: TestClient,
) -> None:
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
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                parent_sample_id=image.sample_id,
                x=2,
                y=0,
                width=3,
                height=2,
                segmentation_mask=[2, 3, 7, 2, 86],
            )
        ],
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/annotations/prepare",
        json={
            "export_format": "segmentation_mask_coco",
            "annotation_collection_id": str(annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    content = json.loads(Path(export_job.export_path).read_text())
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


def test_export_collection_annotations_prepare__pascal_voc(
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
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                parent_sample_id=image.sample_id,
                x=1,
                y=0,
                width=1,
                height=1,
                segmentation_mask=[1, 1, 4],
            )
        ],
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/annotations/prepare",
        json={
            "export_format": "pascal_voc",
            "annotation_collection_id": str(annotation_collection_id),
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    export_dir = Path(export_job.export_path)
    assert (export_dir / "class_id_to_name.json").exists()
    assert (export_dir / "SegmentationClass" / "img1.png").exists()


def test_export_collection_annotations_prepare__unsupported_format(
    db_session: Session,
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = create_collection(session=db_session)
    generate_annotations_export = mock.Mock()
    make_temp_dir = mock.Mock()
    monkeypatch.setattr(export_api, "_generate_annotations_export", generate_annotations_export)
    monkeypatch.setattr(tempfile, "mkdtemp", make_temp_dir)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/annotations/prepare",
        json={"export_format": "youtube_vis_segmentation"},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert response.json() == {
        "detail": "Export format 'youtube_vis_segmentation' is not supported for this endpoint."
    }
    generate_annotations_export.assert_not_called()
    make_temp_dir.assert_not_called()


def test_export_collection_annotations_prepare__image_filter(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # image_a is included via image_filter; image_b is excluded.
    collection = create_collection(session=db_session)
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img_a.jpg",
        width=100,
        height=100,
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img_b.jpg",
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
                parent_sample_id=image_a.sample_id,
                x=10,
                y=20,
                width=30,
                height=40,
            ),
            AnnotationCreate(
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                parent_sample_id=image_b.sample_id,
                x=10,
                y=20,
                width=30,
                height=40,
            ),
        ],
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/annotations/prepare",
        json={
            "export_format": "object_detection_coco",
            "annotation_collection_id": str(annotation_collection_id),
            "image_filter": {
                "filter_type": "image",
                "sample_filter": {"sample_ids": [str(image_a.sample_id)]},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    content = json.loads(Path(export_job.export_path).read_text())
    assert len(content["images"]) == 1
    assert content["images"][0]["file_name"] == "img_a.jpg"


def test_export_collection_captions_prepare(
    db_session: Session,
    test_client: TestClient,
) -> None:
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
        text="a cat on a mat",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/captions/prepare",
        json={},
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    content = json.loads(Path(export_job.export_path).read_text())
    assert content == {
        "images": [{"id": 0, "file_name": "img1.jpg", "width": 100, "height": 100}],
        "annotations": [{"id": 0, "image_id": 0, "caption": "a cat on a mat"}],
    }


def test_export_collection_captions_prepare__image_filter(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # image_a is included via image_filter; image_b is excluded.
    collection = create_collection(session=db_session)
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img_a.jpg",
        width=100,
        height=100,
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="img_b.jpg",
        width=100,
        height=100,
    )
    create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=image_a.sample_id,
        text="caption for a",
    )
    create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=image_b.sample_id,
        text="caption for b",
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/captions/prepare",
        json={
            "image_filter": {
                "filter_type": "image",
                "sample_filter": {"sample_ids": [str(image_a.sample_id)]},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    content = json.loads(Path(export_job.export_path).read_text())
    assert len(content["images"]) == 1
    assert content["images"][0]["file_name"] == "img_a.jpg"
    assert len(content["annotations"]) == 1
    assert content["annotations"][0]["caption"] == "caption for a"


def test_export_collection_youtube_vis_prepare(
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
                dataset_id=collection.dataset_id,
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
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                x=0,
                y=1,
                width=1,
                height=1,
                segmentation_mask=[1, 1, 4],
                object_track_id=object_track_id,
            )
        ],
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/youtube-vis/prepare",
        json={},
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    content = json.loads(Path(export_job.export_path).read_text())
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


def test_export_collection_youtube_vis_prepare__wrong_collection_type(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/youtube-vis/prepare",
        json={},
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_export_collection_youtube_vis_prepare__video_filter(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # video_a is included via video_filter; video_b is excluded.
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_a = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="video_a.mp4", width=3, height=2, duration_s=1.0, fps=1.0),
    )
    create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="video_b.mp4", width=3, height=2, duration_s=1.0, fps=1.0),
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/export/youtube-vis/prepare",
        json={
            "video_filter": {
                "filter_type": "video",
                "sample_filter": {"sample_ids": [str(video_a.video_sample_id)]},
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    export_key = UUID(response.json()["export_key"])

    export_job = db_session.get(ExportJobTable, export_key)
    assert export_job is not None
    content = json.loads(Path(export_job.export_path).read_text())
    assert len(content["videos"]) == 1
    assert content["videos"][0]["file_names"] == ["video_a.mp4/00000.jpg"]
