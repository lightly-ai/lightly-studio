"""Tests for resolving an MCAP sample to its recording."""

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.mcap import recording_source
from lightly_studio.dataset import env
from lightly_studio.errors import NotFoundError
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import create_collection


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


def test_resolve_recording_path(db_session: Session, mocker: MockerFixture) -> None:
    sample = _create_mcap_sample(session=db_session)
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_RECORDING_PATH", "/data/drive.mcap")

    path = recording_source.resolve_recording_path(session=db_session, sample_id=sample.sample_id)

    assert path == "/data/drive.mcap"


def test_resolve_recording_path__unknown_sample(db_session: Session, mocker: MockerFixture) -> None:
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_RECORDING_PATH", "/data/drive.mcap")

    with pytest.raises(NotFoundError, match="MCAP sample not found"):
        recording_source.resolve_recording_path(session=db_session, sample_id=uuid4())


def test_resolve_recording_path__no_recording_configured(
    db_session: Session, mocker: MockerFixture
) -> None:
    sample = _create_mcap_sample(session=db_session)
    mocker.patch.object(env, "LIGHTLY_STUDIO_MCAP_RECORDING_PATH", None)

    with pytest.raises(NotFoundError, match="No recording is configured"):
        recording_source.resolve_recording_path(session=db_session, sample_id=sample.sample_id)
