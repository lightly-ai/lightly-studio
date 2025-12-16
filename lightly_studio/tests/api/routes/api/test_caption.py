from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.resolvers import caption_resolver
from tests.helpers_resolvers import create_caption, create_dataset, create_image


def test_update_caption_text(db_session: Session, test_client: TestClient) -> None:
    # Initialize a dataset and add a caption
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.collection_id
    parent_sample = create_image(session=db_session, dataset_id=dataset_id)
    caption = create_caption(
        session=db_session,
        dataset_id=dataset_id,
        parent_sample_id=parent_sample.sample_id,
    )

    # Update the text of the caption.
    sample_id = caption.sample_id
    new_text = "updated text"
    response = test_client.put(
        f"/api/datasets/{dataset_id!s}/captions/{sample_id!s}",
        json=new_text,
    )

    # Verify that the response includes the updated caption.
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["sample_id"] == str(sample_id)
    assert result["text"] == new_text

    # Verify that the db entry changed by fetching it via the get endpoint.
    updated_caption = caption_resolver.get_by_ids(db_session, sample_ids=[sample_id])[0]
    assert updated_caption.text == new_text


def test_get_caption(db_session: Session, test_client: TestClient) -> None:
    # Initialize a dataset and add a caption
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.collection_id
    parent_sample = create_image(session=db_session, dataset_id=dataset_id)
    caption = create_caption(
        session=db_session,
        dataset_id=dataset_id,
        parent_sample_id=parent_sample.sample_id,
        text="test caption",
    )

    sample_id = caption.sample_id
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions/{sample_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["sample_id"] == str(sample_id)
    assert result["text"] == "test caption"


def test_create_caption(db_session: Session, test_client: TestClient) -> None:
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.collection_id
    sample = create_image(session=db_session, dataset_id=dataset_id)
    input_data = {
        "parent_sample_id": str(sample.sample_id),
        "text": "added caption",
    }
    response = test_client.post(f"/api/datasets/{dataset_id!s}/captions", json=input_data)

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    new_sample_id = UUID(result["sample_id"])

    caption = caption_resolver.get_by_ids(db_session, sample_ids=[new_sample_id])[0]
    assert caption.text == "added caption"
    assert len(sample.sample.captions) == 1
    assert sample.sample.captions[0].sample_id == new_sample_id

    # Check that wrong parent_sample_id throws error
    wrong_sample_id = str(uuid4())
    input_data = {
        "parent_sample_id": wrong_sample_id,
        "text": "added caption",
    }
    response = test_client.post(f"/api/datasets/{dataset_id!s}/captions", json=input_data)
    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    result = response.json()
    assert result["error"] == f"Sample with ID {wrong_sample_id} not found."


def test_delete_caption(db_session: Session, test_client: TestClient) -> None:
    # Initialize a dataset and add a caption
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.collection_id
    parent_sample = create_image(session=db_session, dataset_id=dataset_id)
    caption = create_caption(
        session=db_session,
        dataset_id=dataset_id,
        parent_sample_id=parent_sample.sample_id,
    )
    sample_id = caption.sample_id

    delete_response = test_client.delete(f"/api/datasets/{dataset_id}/captions/{sample_id}")
    assert delete_response.status_code == HTTP_STATUS_OK
    assert delete_response.json() == {"status": "deleted"}

    # Try to delete again and expect a 404
    delete_response = test_client.delete(f"/api/datasets/{dataset_id}/captions/{sample_id}")
    assert delete_response.status_code == HTTP_STATUS_NOT_FOUND
    assert delete_response.json() == {"detail": "Caption not found"}
