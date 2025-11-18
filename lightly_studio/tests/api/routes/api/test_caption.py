from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.resolvers import caption_resolver
from tests.conftest import CaptionsTestData


@pytest.fixture
def dataset_id(captions_test_data: CaptionsTestData) -> UUID:
    return captions_test_data.datasets[0].dataset_id


def test_update_caption_text(
    db_session: Session,
    test_client: TestClient,
    dataset_id: UUID,
    captions_test_data: CaptionsTestData,
) -> None:
    # Update the text of a caption.
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
    caption_id = captions_test_data.captions[0].caption_id
    text_db = captions_test_data.captions[0].text
    response = test_client.get(
        f"/api/datasets/{dataset_id}/captions/{caption_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["caption_id"] == str(caption_id)
    assert result["text"] == text_db
