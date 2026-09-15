"""Tests for GET /recordings/{recording_id}."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from fastapi.responses import Response
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import recording_resolver
from tests.helpers_resolvers import create_collection

_PATCH_FILE_INFO = "lightly_studio.api.routes.recordings.get_recording.byte_range.file_info"
_PATCH_SERVE_FILE = "lightly_studio.api.routes.recordings.get_recording.byte_range.serve_file"


def test_get_recording(media_test_client: TestClient, db_session: Session) -> None:
    collection = create_collection(session=db_session)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/data/recording.mcap",
        format_=RecordingFormat.MCAP,
    )

    with patch(_PATCH_FILE_INFO), patch(_PATCH_SERVE_FILE) as mock_serve:
        mock_serve.return_value = Response(content=b"bytes", status_code=HTTP_STATUS_OK)
        response = media_test_client.get(f"/recordings/{recording_id}")

    assert response.status_code == HTTP_STATUS_OK
    mock_serve.assert_called_once()


def test_get_recording__not_found(media_test_client: TestClient) -> None:
    response = media_test_client.get(f"/recordings/{uuid4()}")
    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_recording__file_not_found(media_test_client: TestClient, db_session: Session) -> None:
    collection = create_collection(session=db_session)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/data/recording.mcap",
        format_=RecordingFormat.MCAP,
    )

    with patch(_PATCH_FILE_INFO, side_effect=FileNotFoundError("missing")):
        response = media_test_client.get(f"/recordings/{recording_id}")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
