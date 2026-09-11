"""Tests for recording_resolver.create."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import recording_resolver
from tests.helpers_resolvers import create_collection


def test_create(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/data/recording.mcap",
        format_=RecordingFormat.MCAP,
    )

    recording = recording_resolver.get_by_id(session=db_session, recording_id=recording_id)
    assert recording is not None
    assert recording.recording_id == recording_id
    assert recording.dataset_id == collection.dataset_id
    assert recording.uri == "/data/recording.mcap"
    assert recording.format == RecordingFormat.MCAP


def test_create__missing_dataset(db_session: Session) -> None:
    with pytest.raises(ValueError, match="not found"):
        recording_resolver.create(
            session=db_session,
            dataset_id=uuid4(),
            uri="/data/recording.mcap",
            format_=RecordingFormat.MCAP,
        )


@pytest.mark.parametrize("uri", ["", "   "])
def test_create__empty_uri(db_session: Session, uri: str) -> None:
    collection = create_collection(session=db_session)

    with pytest.raises(ValueError, match="uri"):
        recording_resolver.create(
            session=db_session,
            dataset_id=collection.dataset_id,
            uri=uri,
            format_=RecordingFormat.MCAP,
        )


def test_create__duplicate_uri_allowed(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    recording_id_1 = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/data/recording.mcap",
        format_=RecordingFormat.MCAP,
    )
    recording_id_2 = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/data/recording.mcap",
        format_=RecordingFormat.MCAP,
    )

    assert recording_id_1 != recording_id_2
    assert recording_resolver.get_by_id(session=db_session, recording_id=recording_id_1) is not None
    assert recording_resolver.get_by_id(session=db_session, recording_id=recording_id_2) is not None
