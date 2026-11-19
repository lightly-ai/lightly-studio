from dataclasses import dataclass
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_OK
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_caption,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video, create_video_with_frames


@dataclass
class VideoCollection:
    collection_id: UUID
    ids: dict[str, UUID]


@pytest.fixture
def videos(db_session: Session) -> VideoCollection:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id
    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="person"
    )
    ids = {}
    for name, width, duration in [
        ("first.mp4", 800, 2),
        ("second.mp4", 800, 2),
        ("narrow.mp4", 600, 2),
        ("empty.mp4", 800, 0),
    ]:
        video = create_video_with_frames(
            session=db_session,
            collection_id=collection_id,
            video=VideoStub(path=f"/videos/{name}", width=width, duration_s=duration, fps=1),
        )
        ids[name] = video.video_sample_id
        create_caption(
            session=db_session,
            collection_id=collection_id,
            parent_sample_id=video.video_sample_id,
            text="caption",
        )
        if duration:
            create_annotations(
                session=db_session,
                collection_id=collection_id,
                annotations=[
                    AnnotationDetails(
                        sample_id=video.video_sample_id,
                        annotation_label_id=label.annotation_label_id,
                        annotation_type=AnnotationType.CLASSIFICATION,
                        start_time_s=start,
                        end_time_s=start + 1,
                    )
                    for start in (0, 1)
                ],
            )
    return VideoCollection(collection_id=collection_id, ids=ids)


@pytest.fixture(
    params=[
        ("video_event_match_expr", "event", "start_time_s"),
        ("video_frame_match_expr", "video_frame", "frame_timestamp_s"),
    ],
    ids=["event", "frame"],
)
def expression(request: pytest.FixtureRequest) -> dict[str, object]:
    node_type, table, field_name = request.param
    return {
        "type": node_type,
        "subexpr": {
            "type": "ordinal_float_expr",
            "field": {"table": table, "name": field_name},
            "operator": "<=",
            "value": 1,
        },
    }


@pytest.fixture
def video_filter(expression: dict[str, object]) -> dict[str, object]:
    return {
        "filter": {
            "width": {"min": 700},
            "sample_filter": {"query_expr": {"match_expr": expression}},
        }
    }


def test_video_queries__pages_and_counts(
    test_client: TestClient, videos: VideoCollection, video_filter: dict[str, object]
) -> None:
    names: list[str] = []
    for offset, next_cursor, page_size in [(0, 1, 1), (1, None, 1), (2, None, 0)]:
        response = test_client.post(
            f"/api/collections/{videos.collection_id}/video/",
            params={"cursor": offset, "limit": 1},
            json=video_filter,
        )
        assert response.status_code == HTTP_STATUS_OK
        result = response.json()
        assert result["total_count"] == 2
        assert result["nextCursor"] == next_cursor
        assert len(result["data"]) == page_size
        names.extend(video["file_name"] for video in result["data"])
    assert sorted(names) == ["first.mp4", "second.mp4"]


def test_video_queries__sample_ids(
    test_client: TestClient, videos: VideoCollection, video_filter: dict[str, object]
) -> None:
    response = test_client.post(
        f"/api/collections/{videos.collection_id}/video/sample_ids", json=video_filter
    )
    assert response.status_code == HTTP_STATUS_OK
    assert sorted(UUID(value) for value in response.json()) == sorted(
        [videos.ids["first.mp4"], videos.ids["second.mp4"]]
    )


def test_video_queries__generic_sample_pages_and_caption_counts(
    test_client: TestClient, videos: VideoCollection, expression: dict[str, object]
) -> None:
    width = {
        "type": "integer_expr",
        "field": {"table": "video", "name": "width"},
        "operator": ">",
        "value": 700,
    }
    query = {"type": "and", "children": [expression, width]}
    returned_ids: list[UUID] = []
    for offset, next_cursor, page_size in [(0, 1, 1), (1, None, 1), (2, None, 0)]:
        response = test_client.post(
            f"/api/collections/{videos.collection_id}/samples/list",
            params={"cursor": offset, "limit": 1},
            json={"filters": {"query_expr": {"match_expr": query}}},
        )
        assert response.status_code == HTTP_STATUS_OK
        result = response.json()
        assert result["total_count"] == result["total_caption_count"] == 2
        assert result["nextCursor"] == next_cursor
        assert len(result["data"]) == page_size
        returned_ids.extend(UUID(sample["sample_id"]) for sample in result["data"])
    assert sorted(returned_ids) == sorted([videos.ids["first.mp4"], videos.ids["second.mp4"]])


@pytest.mark.parametrize("node_type", ["video_event_match_expr", "video_frame_match_expr"])
@pytest.mark.parametrize("endpoint", ["images", "samples"])
def test_video_queries__reject_image_collection(
    test_client: TestClient,
    db_session: Session,
    node_type: str,
    endpoint: str,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    expression = {
        "type": "not",
        "child": {
            "type": node_type,
            "subexpr": {
                "type": "ordinal_float_expr",
                "field": {"table": "event", "name": "start_time_s"},
                "operator": "<",
                "value": 5,
            },
        },
    }
    filters = {"query_expr": {"match_expr": expression}}
    response = test_client.post(
        f"/api/collections/{collection.collection_id}/{endpoint}/list",
        json={"filters": {"sample_filter": filters} if endpoint == "images" else filters},
    )
    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    assert "video collection" in response.json()["error"]


def test_fps_comparison__float_bounds(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    for fps in (24, 29.97, 30):
        create_video(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path=f"/videos/{fps}.mp4", fps=fps),
        )

    all_names = ["24.mp4", "29.97.mp4", "30.mp4"]
    for operator, bound, names in [
        ("==", 29.97, ["29.97.mp4"]),
        ("!=", 29.97, ["24.mp4", "30.mp4"]),
        (">", 29.97, ["30.mp4"]),
        (">=", 29.97, ["29.97.mp4", "30.mp4"]),
        ("<", 1e100, all_names),
        (">", -1e100, all_names),
    ]:
        expression = {
            "type": "ordinal_float_expr",
            "field": {"table": "video", "name": "fps"},
            "operator": operator,
            "value": bound,
        }
        response = test_client.post(
            f"/api/collections/{collection.collection_id}/video/",
            json={"filter": {"sample_filter": {"query_expr": {"match_expr": expression}}}},
        )
        assert response.status_code == HTTP_STATUS_OK
        assert sorted(video["file_name"] for video in response.json()["data"]) == names


def test_duration_comparison__bounds_near_zero(
    test_client: TestClient, videos: VideoCollection
) -> None:
    for operator, bound, names in [
        (">=", 1e-50, ["first.mp4", "narrow.mp4", "second.mp4"]),
        ("<=", -1e-50, []),
        ("==", 1e-50, []),
        ("==", 0.0, ["empty.mp4"]),
    ]:
        expression = {
            "type": "ordinal_float_expr",
            "field": {"table": "video", "name": "duration_s"},
            "operator": operator,
            "value": bound,
        }
        response = test_client.post(
            f"/api/collections/{videos.collection_id}/video/",
            json={"filter": {"sample_filter": {"query_expr": {"match_expr": expression}}}},
        )
        assert response.status_code == HTTP_STATUS_OK
        assert sorted(video["file_name"] for video in response.json()["data"]) == names
