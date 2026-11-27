from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample_query import (
    MetadataRecord,
    SampleInclude,
    SamplePage,
    SampleQueryRequest,
)
from lightly_studio.resolvers import metadata_resolver, tag_resolver
from lightly_studio.services.sample_services import sample_query_service
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_caption,
    create_collection,
    create_image,
    create_tag,
)


def test_v1_query_samples__pages(test_client: TestClient, db_session: Session) -> None:
    collection_id = create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    ).collection_id
    for path in ["/a.png", "/b.png", "/c.png"]:
        create_image(session=db_session, collection_id=collection_id, file_path_abs=path)
    url = f"/api/v1/collections/{collection_id}/samples:query"
    sort = [{"field": {"table": "image", "name": "file_name"}, "direction": "desc"}]

    first = test_client.post(url, json={"sort": sort, "limit": 2}).json()
    second = test_client.post(
        url, json={"sort": sort, "limit": 2, "cursor": first["next_cursor"]}
    ).json()

    assert [s["file_name"] for s in first["samples"]] == ["c.png", "b.png"]
    assert [s["file_name"] for s in second["samples"]] == ["a.png"]
    assert second["next_cursor"] is None


def test_v1_query_samples__include_all(test_client: TestClient, db_session: Session) -> None:
    collection_id = create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    ).collection_id
    image = create_image(session=db_session, collection_id=collection_id)
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="tag")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[image.sample_id]
    )
    metadata_resolver.bulk_update_metadata(
        session=db_session,
        sample_metadata=[(image.sample_id, {"gps": GPSCoordinate(lat=1.5, lon=2.5)})],
    )
    create_caption(
        session=db_session, collection_id=collection_id, parent_sample_id=image.sample_id
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    request = SampleQueryRequest(include=list(SampleInclude))

    response = test_client.post(
        f"/api/v1/collections/{collection_id}/samples:query",
        json=request.model_dump(mode="json"),
    )

    expected = sample_query_service.query_samples(
        session=db_session, collection_id=collection_id, request=request
    )
    assert SamplePage.model_validate(response.json()) == expected
    [sample] = expected.samples
    assert sample.tags == ["tag"]
    assert sample.metadata == MetadataRecord(
        data={"gps": {"lat": 1.5, "lon": 2.5}}, metadata_schema={"gps": "gps_coordinate"}
    )
    assert sample.captions is not None
    assert sample.annotations is not None
    assert (len(sample.captions), len(sample.annotations)) == (1, 1)


@pytest.mark.parametrize(
    ("body", "status_code"),
    [
        ({"cursor": "not a cursor"}, HTTP_STATUS_BAD_REQUEST),
        ({"limit": 1001}, HTTP_STATUS_UNPROCESSABLE_ENTITY),
        ({"cursor": "x", "offset": 1}, HTTP_STATUS_UNPROCESSABLE_ENTITY),
    ],
)
def test_v1_query_samples__bad_request(
    test_client: TestClient, db_session: Session, body: dict[str, object], status_code: int
) -> None:
    collection_id = create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    ).collection_id

    response = test_client.post(f"/api/v1/collections/{collection_id}/samples:query", json=body)

    assert response.status_code == status_code


def test_v1_query_samples__video_collection(test_client: TestClient, db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    response = test_client.post(
        f"/api/v1/collections/{collection.collection_id}/samples:query", json={}
    )

    assert response.status_code == HTTP_STATUS_BAD_REQUEST


def test_v1_query_samples__not_found(test_client: TestClient) -> None:
    collection_id = UUID("00000000-0000-0000-0000-000000000001")

    response = test_client.post(f"/api/v1/collections/{collection_id}/samples:query", json={})

    assert response.status_code == HTTP_STATUS_NOT_FOUND
