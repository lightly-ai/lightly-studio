from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
)
from lightly_studio.dataset.caption_segment_matching import CAPTION_SEGMENT_MATCH_SCORE_KEY
from lightly_studio.resolvers import caption_resolver, metadata_resolver
from tests.helpers_resolvers import create_caption, create_collection, create_image


def test_update_caption_text(db_session: Session, test_client: TestClient) -> None:
    # Initialize a collection and add a caption
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    parent_sample = create_image(session=db_session, collection_id=collection_id)
    caption = create_caption(
        session=db_session,
        collection_id=collection_id,
        parent_sample_id=parent_sample.sample_id,
    )

    # Update the text of the caption.
    sample_id = caption.sample_id
    new_text = "updated text"
    response = test_client.put(
        f"/api/collections/{collection_id!s}/captions/{sample_id!s}",
        json={"text": new_text},
    )

    # Verify that the response includes the updated caption.
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["sample_id"] == str(sample_id)
    assert result["text"] == new_text

    # Verify that the db entry changed by fetching it via the get endpoint.
    updated_caption = caption_resolver.get_by_ids(db_session, sample_ids=[sample_id])[0]
    assert updated_caption.text == new_text


def test_update_caption_text__marks_narration_classification_stale(
    db_session: Session,
    test_client: TestClient,
) -> None:
    collection = create_collection(session=db_session)
    parent_sample = create_image(session=db_session, collection_id=collection.collection_id)
    caption = create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=parent_sample.sample_id,
    )
    metadata_resolver.bulk_update_metadata(
        session=db_session,
        sample_metadata=[
            (
                parent_sample.sample_id,
                {
                    "narration_qa_status": "likely_pass",
                    "narration_classification_complete": True,
                    "narration_classification_stale": False,
                    "narration_classification_error": "",
                },
            ),
            (
                caption.sample_id,
                {"narration_label": "TASK", "narration_classification_stale": False},
            ),
        ],
    )

    response = test_client.put(
        f"/api/collections/{collection.collection_id}/captions/{caption.sample_id}",
        json={"text": "changed narration"},
    )

    assert response.status_code == HTTP_STATUS_OK
    parent_metadata = metadata_resolver.get_by_sample_id(
        session=db_session,
        sample_id=parent_sample.sample_id,
    )
    caption_metadata = metadata_resolver.get_by_sample_id(
        session=db_session,
        sample_id=caption.sample_id,
    )
    assert parent_metadata is not None
    assert parent_metadata.data["narration_qa_status"] == "incomplete"
    assert parent_metadata.data["narration_classification_complete"] is False
    assert caption_metadata is not None
    assert caption_metadata.data["narration_classification_stale"] is True


def test_get_caption(db_session: Session, test_client: TestClient) -> None:
    # Initialize a collection and add a caption
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    parent_sample = create_image(session=db_session, collection_id=collection_id)
    caption = create_caption(
        session=db_session,
        collection_id=collection_id,
        parent_sample_id=parent_sample.sample_id,
        text="test caption",
    )

    sample_id = caption.sample_id
    response = test_client.get(
        f"/api/collections/{collection_id}/captions/{sample_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["sample_id"] == str(sample_id)
    assert result["text"] == "test caption"


def test_get_caption__with_metadata(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    parent_sample = create_image(session=db_session, collection_id=collection_id)
    caption = create_caption(
        session=db_session,
        collection_id=collection_id,
        parent_sample_id=parent_sample.sample_id,
    )
    metadata_resolver.set_value_for_sample(
        session=db_session,
        sample_id=caption.sample_id,
        key=CAPTION_SEGMENT_MATCH_SCORE_KEY,
        value=0.75,
    )

    response = test_client.get(
        f"/api/collections/{collection_id}/captions/{caption.sample_id}",
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["metadata_dict"]["data"] == {CAPTION_SEGMENT_MATCH_SCORE_KEY: 0.75}


def test_create_caption(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    sample = create_image(session=db_session, collection_id=collection_id)
    input_data = {
        "parent_sample_id": str(sample.sample_id),
        "text": "added caption",
    }
    response = test_client.post(f"/api/collections/{collection_id!s}/captions", json=input_data)

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
    response = test_client.post(f"/api/collections/{collection_id!s}/captions", json=input_data)
    assert response.status_code == HTTP_STATUS_BAD_REQUEST
    result = response.json()
    assert result["error"] == f"Sample with ID {wrong_sample_id} not found."


def test_create_caption__with_temporal_span(db_session: Session, test_client: TestClient) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    sample = create_image(session=db_session, collection_id=collection_id)
    input_data = {
        "parent_sample_id": str(sample.sample_id),
        "text": "captioned segment",
        "start_time_s": 1.0,
        "end_time_s": 2.5,
    }
    response = test_client.post(f"/api/collections/{collection_id!s}/captions", json=input_data)

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["temporal_span_details"] == {"start_time_s": 1.0, "end_time_s": 2.5}


def test_update_caption_text_and_temporal_span(
    db_session: Session, test_client: TestClient
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    parent_sample = create_image(session=db_session, collection_id=collection_id)
    caption = create_caption(
        session=db_session,
        collection_id=collection_id,
        parent_sample_id=parent_sample.sample_id,
    )
    sample_id = caption.sample_id

    response = test_client.put(
        f"/api/collections/{collection_id!s}/captions/{sample_id!s}",
        json={"text": "new text", "start_time_s": 1.0, "end_time_s": 2.0},
    )

    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["text"] == "new text"
    assert result["temporal_span_details"] == {"start_time_s": 1.0, "end_time_s": 2.0}


def test_delete_caption(db_session: Session, test_client: TestClient) -> None:
    # Initialize a collection and add a caption
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    parent_sample = create_image(session=db_session, collection_id=collection_id)
    caption = create_caption(
        session=db_session,
        collection_id=collection_id,
        parent_sample_id=parent_sample.sample_id,
    )
    sample_id = caption.sample_id

    delete_response = test_client.delete(f"/api/collections/{collection_id}/captions/{sample_id}")
    assert delete_response.status_code == HTTP_STATUS_OK
    assert delete_response.json() == {"status": "deleted"}

    # Try to delete again and expect a 404
    delete_response = test_client.delete(f"/api/collections/{collection_id}/captions/{sample_id}")
    assert delete_response.status_code == HTTP_STATUS_NOT_FOUND
    assert delete_response.json() == {"detail": "Caption not found"}
