
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_OK,
)
from lightly_studio.resolvers import (
    tag_resolver,
)
from tests.helpers_resolvers import create_dataset, create_image, create_tag


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
