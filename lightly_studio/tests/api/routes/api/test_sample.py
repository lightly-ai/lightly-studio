from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_OK,
)
from lightly_studio.resolvers import (
    tag_resolver,
)
from tests.helpers_resolvers import (
    ImageStub,
    create_dataset,
    create_image,
    create_images,
    create_tag,
)


def test_read_samples__get_all(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # Create samples
    dataset = create_dataset(session=db_session)
    samples = create_images(
        db_session=db_session,
        dataset_id=dataset.dataset_id,
        images=[ImageStub(path="sample1.jpg"), ImageStub(path="sample2.jpg")],
    )
    # Sort samples by (created_at, sample_id) to match the expected order
    samples.sort(key=lambda x: (x.created_at, x.sample_id))

    # Call the API
    response = test_client.post("/api/samples/list", json={})
    assert response.status_code == HTTP_STATUS_OK

    # Assert the response
    assert response.json()["total_count"] == 2
    response_samples = response.json()["data"]
    assert len(response_samples) == 2
    assert response_samples[0]["sample_id"] == str(samples[0].sample_id)
    assert response_samples[1]["sample_id"] == str(samples[1].sample_id)


def test_read_samples__get_all_empty(
    test_client: TestClient,
) -> None:
    # Call the API
    response = test_client.post("/api/samples/list", json={})
    assert response.status_code == HTTP_STATUS_OK

    # Assert the response
    assert response.json()["total_count"] == 0
    assert len(response.json()["data"]) == 0


def test_read_samples__pagination(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # Create samples
    dataset = create_dataset(session=db_session)
    samples = create_images(
        db_session=db_session,
        dataset_id=dataset.dataset_id,
        images=[
            ImageStub(path="sample1.jpg"),
            ImageStub(path="sample2.jpg"),
            ImageStub(path="sample3.jpg"),
            ImageStub(path="sample4.jpg"),
        ],
    )
    # Sort samples by (created_at, sample_id) to match the expected order
    samples.sort(key=lambda x: (x.created_at, x.sample_id))

    # Call the API
    json_body = {
        "pagination": {
            "offset": 1,
            "limit": 2,
        }
    }
    response = test_client.post("/api/samples/list", json=json_body)
    assert response.status_code == HTTP_STATUS_OK

    # Assert the response
    assert response.json()["total_count"] == 4
    response_samples = response.json()["data"]
    assert len(response_samples) == 2
    assert response_samples[0]["sample_id"] == str(samples[1].sample_id)
    assert response_samples[1]["sample_id"] == str(samples[2].sample_id)


def test_read_samples__filters(
    db_session: Session,
    test_client: TestClient,
) -> None:
    # Create samples
    dataset = create_dataset(session=db_session)
    samples = create_images(
        db_session=db_session,
        dataset_id=dataset.dataset_id,
        images=[
            ImageStub(path="sample1.jpg"),
            ImageStub(path="sample2.jpg"),
            ImageStub(path="sample3.jpg"),
            ImageStub(path="sample4.jpg"),
        ],
    )

    # Call the API
    json_body = {
        "filters": {
            "sample_ids": [str(samples[1].sample_id), str(samples[3].sample_id)],
        }
    }
    response = test_client.post("/api/samples/list", json=json_body)
    assert response.status_code == HTTP_STATUS_OK

    # Assert the response
    assert response.json()["total_count"] == 2
    response_samples = response.json()["data"]
    assert len(response_samples) == 2
    assert {response_samples[0]["sample_id"], response_samples[1]["sample_id"]} == {
        str(samples[1].sample_id),
        str(samples[3].sample_id),
    }


def test_add_tag_to_sample_calls_add_tag_to_sample(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.dataset_id
    image = create_image(session=db_session, dataset_id=dataset_id)
    tag = create_tag(session=db_session, dataset_id=dataset_id)
    sample_id = image.sample_id
    tag_id = tag.tag_id

    assert len(image.sample.tags) == 0

    # Make the request to add sample to a tag
    response = test_client.post(f"/api/datasets/{dataset_id}/samples/{sample_id}/tag/{tag_id}")

    # Assert the response
    assert response.status_code == HTTP_STATUS_CREATED

    # Assert that the tag was added
    assert len(image.sample.tags) == 1


def test_remove_tag_from_sample_calls_remove_tag_from_sample(
    db_session: Session,
    test_client: TestClient,
) -> None:
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.dataset_id
    image = create_image(session=db_session, dataset_id=dataset_id)
    sample_id = image.sample_id
    tag = create_tag(session=db_session, dataset_id=dataset_id)
    tag_id = tag.tag_id

    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag_id, sample=image.sample)
    assert len(image.sample.tags) == 1

    # Make the request to add sample to a tag
    response = test_client.delete(f"/api/datasets/{dataset_id}/samples/{sample_id}/tag/{tag_id}")

    # Assert the response
    assert response.status_code == HTTP_STATUS_OK

    # Assert that the tag was removed
    assert len(image.sample.tags) == 0
