"""Parent track class names in annotation, frame, and video responses."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import object_track_resolver
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


@pytest.mark.parametrize(
    ("method", "url_template", "annotation_path"),
    [
        ("GET", "/collections/{collection_id}/annotations/{annotation_id}", ()),
        ("GET", "/collections/{collection_id}/frame/{frame_id}", ("sample", "annotations", 0)),
        (
            "POST",
            "/collections/{frame_collection_id}/frame/",
            ("data", 0, "sample", "annotations", 0),
        ),
        ("GET", "/videos/{video_id}", ("frame", "sample", "annotations", 0)),
        (
            "POST",
            "/collections/{collection_id}/video/",
            ("data", 0, "frame", "sample", "annotations", 0),
        ),
    ],
)
def test_get_frame_annotations__parent_track_class_name(
    test_client: TestClient,
    db_session: Session,
    method: str,
    url_template: str,
    annotation_path: tuple[str | int, ...],
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="truck.mp4", duration_s=2, fps=1),
    )
    parent_track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[ObjectTrackCreate(dataset_id=collection.dataset_id, object_track_number=7)],
    )[0]
    child_track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                dataset_id=collection.dataset_id,
                object_track_number=8,
                parent_object_track_id=parent_track_id,
            )
        ],
    )[0]
    parent_class = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="truck"
    )
    child_class = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cabin"
    )
    create_annotation(
        session=db_session,
        collection_id=video.video_frames_collection_id,
        sample_id=video.frame_sample_ids[1],
        annotation_label_id=parent_class.annotation_label_id,
        annotation_data={"object_track_id": parent_track_id},
    )
    child_annotation = create_annotation(
        session=db_session,
        collection_id=video.video_frames_collection_id,
        sample_id=video.frame_sample_ids[0],
        annotation_label_id=child_class.annotation_label_id,
        annotation_data={"object_track_id": child_track_id},
    )
    url = url_template.format(
        collection_id=collection.collection_id,
        annotation_id=child_annotation.sample_id,
        frame_id=video.frame_sample_ids[0],
        frame_collection_id=video.video_frames_collection_id,
        video_id=video.video_sample_id,
    )

    response = test_client.request(method=method, url=f"/api{url}", json={})

    assert response.status_code == HTTP_STATUS_OK
    annotation = response.json()
    for key in annotation_path:
        annotation = annotation[key]
    assert annotation["object_track_number"] == 8
    assert annotation["parent_object_track_number"] == 7
    assert annotation["parent_object_track_class_name"] == "truck"
