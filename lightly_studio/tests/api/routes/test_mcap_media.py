"""Tests for serving MCAP recordings as byte ranges."""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api import status
from lightly_studio.dataset import env
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import create_collection

RECORDING_BYTES = bytes(range(256))


def _create_recording(tmp_path: Path, mocker: MockerFixture) -> Path:
    recording = tmp_path / "drive.mcap"
    recording.write_bytes(RECORDING_BYTES)
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_RECORDING_PATH", str(recording))
    return recording


def _create_mcap_sample(session: Session) -> SampleTable:
    collection = create_collection(session=session, sample_type=SampleType.MCAP)
    sample = SampleTable(collection_id=collection.collection_id)
    session.add(sample)
    session.commit()
    session.add(
        McapTable(
            sample_id=sample.sample_id,
            channel_id=5,
            log_time_ns=1789000000000000001,
            capture_timestamp_ns=1789000000000000000,
        )
    )
    session.commit()
    return sample


def test_serve_mcap_recording_by_sample_id(
    media_test_client: TestClient, db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    """A range request returns exactly those bytes, and states the recording's length."""
    _create_recording(tmp_path=tmp_path, mocker=mocker)
    sample = _create_mcap_sample(session=db_session)

    response = media_test_client.get(
        f"/mcap/media/{sample.sample_id}", headers={"Range": "bytes=16-31"}
    )

    assert response.status_code == status.HTTP_STATUS_PARTIAL_CONTENT
    assert response.content == RECORDING_BYTES[16:32]
    assert response.headers["Content-Range"] == "bytes 16-31/256"
    assert response.headers["Content-Length"] == "16"
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["ETag"]


def test_serve_mcap_recording_by_sample_id__single_byte_probe(
    media_test_client: TestClient, db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    """The frontend learns the recording's length from a one-byte read."""
    _create_recording(tmp_path=tmp_path, mocker=mocker)
    sample = _create_mcap_sample(session=db_session)

    response = media_test_client.get(
        f"/mcap/media/{sample.sample_id}", headers={"Range": "bytes=0-0"}
    )

    assert response.status_code == status.HTTP_STATUS_PARTIAL_CONTENT
    assert response.headers["Content-Range"] == "bytes 0-0/256"


def test_serve_mcap_recording_by_sample_id__whole_recording(
    media_test_client: TestClient, db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    _create_recording(tmp_path=tmp_path, mocker=mocker)
    sample = _create_mcap_sample(session=db_session)

    response = media_test_client.get(f"/mcap/media/{sample.sample_id}")

    assert response.status_code == status.HTTP_STATUS_OK
    assert response.content == RECORDING_BYTES


def test_serve_mcap_recording_by_sample_id__pins_a_revision(
    media_test_client: TestClient, db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    """A recording that changed under the caller is refused rather than mixed."""
    _create_recording(tmp_path=tmp_path, mocker=mocker)
    sample = _create_mcap_sample(session=db_session)
    url = f"/mcap/media/{sample.sample_id}"
    revision = media_test_client.get(url, headers={"Range": "bytes=0-0"}).headers["ETag"]

    matching = media_test_client.get(url, headers={"Range": "bytes=0-0", "If-Match": revision})
    stale = media_test_client.get(url, headers={"Range": "bytes=0-0", "If-Match": '"stale"'})

    assert matching.status_code == status.HTTP_STATUS_PARTIAL_CONTENT
    assert stale.status_code == status.HTTP_STATUS_PRECONDITION_FAILED


def test_serve_mcap_recording_by_sample_id__unknown_sample(
    media_test_client: TestClient, tmp_path: Path, mocker: MockerFixture
) -> None:
    _create_recording(tmp_path=tmp_path, mocker=mocker)

    response = media_test_client.get(f"/mcap/media/{uuid4()}")

    assert response.status_code == status.HTTP_STATUS_NOT_FOUND


def test_serve_mcap_recording_by_sample_id__no_recording_configured(
    media_test_client: TestClient, db_session: Session, mocker: MockerFixture
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_RECORDING_PATH", None)
    sample = _create_mcap_sample(session=db_session)

    response = media_test_client.get(f"/mcap/media/{sample.sample_id}")

    assert response.status_code == status.HTTP_STATUS_NOT_FOUND


def test_serve_mcap_recording_by_sample_id__missing_recording(
    media_test_client: TestClient, db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_RECORDING_PATH", str(tmp_path / "absent.mcap"))
    sample = _create_mcap_sample(session=db_session)

    response = media_test_client.get(f"/mcap/media/{sample.sample_id}")

    assert response.status_code == status.HTTP_STATUS_NOT_FOUND
