from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_OK
from lightly_studio.resolvers import caption_resolver
from tests.conftest import CaptionsTestData


def test_update_caption_text(
    db_session: Session,
    test_client: TestClient,
    captions_test_data: CaptionsTestData,
) -> None:
    # Update the text of a caption.
    dataset_id = captions_test_data.captions[0].sample.dataset_id
    caption_id = captions_test_data.captions[0].caption_id
    new_text = "updated text"
    response = test_client.put(
        f"/api/datasets/{dataset_id!s}/captions/{caption_id!s}",
        json=new_text,
    )

    # Verify that the response includes the updated caption.
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["caption_id"] == str(caption_id)
    assert result["text"] == new_text

    # Verify that the db entry changed by fetching it via the get endpoint.
    updated_caption = caption_resolver.get_by_ids(db_session, caption_ids=[caption_id])[0]
    assert updated_caption.text == new_text


def test_get_caption(test_client: TestClient, captions_test_data: CaptionsTestData) -> None:
    dataset_id = captions_test_data.captions[0].sample.dataset_id
    caption_id = captions_test_data.captions[0].caption_id
    text_db = captions_test_data.captions[0].text
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions/{caption_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["caption_id"] == str(caption_id)
    assert result["text"] == text_db


def test_create_caption(
    db_session: Session,
    test_client: TestClient,
    captions_test_data: CaptionsTestData,
) -> None:
    dataset_id = captions_test_data.captions[0].sample.dataset_id
    input_data = {
        "parent_sample_id": str(captions_test_data.captions[0].parent_sample_id),
        "text": "added caption",
    }
    response = test_client.post(f"/api/datasets/{dataset_id!s}/captions", json=input_data)

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    new_caption_id = UUID(result["caption_id"])

    captions = caption_resolver.get_all(db_session, dataset_id=dataset_id)
    assert len(captions.captions) == 5

    caption = caption_resolver.get_by_ids(db_session, caption_ids=[new_caption_id])[0]
    assert caption.text == "added caption"

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
