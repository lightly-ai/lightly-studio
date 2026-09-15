"""Tests for recording_resolver.get_by_id."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import recording_resolver
from tests.helpers_resolvers import create_collection


def test_get_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/data/recording.mcap",
        format_=RecordingFormat.MCAP,
    )

    result = recording_resolver.get_by_id(session=db_session, recording_id=recording_id)

    assert result is not None
    assert result.recording_id == recording_id
    assert result.dataset_id == collection.dataset_id
    assert result.uri == "/data/recording.mcap"
    assert result.format == RecordingFormat.MCAP


def test_get_by_id__missing(db_session: Session) -> None:
    result = recording_resolver.get_by_id(session=db_session, recording_id=uuid4())

    assert result is None
