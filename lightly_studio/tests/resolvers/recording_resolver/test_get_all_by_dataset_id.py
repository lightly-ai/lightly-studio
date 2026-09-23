"""Tests for recording_resolver.get_all_by_dataset_id."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import recording_resolver
from tests.helpers_resolvers import create_collection


def test_get_all_by_dataset_id(db_session: Session) -> None:
    collection_a = create_collection(session=db_session)
    collection_b = create_collection(session=db_session)
    recording_id_1 = recording_resolver.create(
        session=db_session,
        dataset_id=collection_a.dataset_id,
        uri="/data/a1.mcap",
        format_=RecordingFormat.MCAP,
    )
    recording_id_2 = recording_resolver.create(
        session=db_session,
        dataset_id=collection_a.dataset_id,
        uri="/data/a2.mcap",
        format_=RecordingFormat.MCAP,
    )
    recording_resolver.create(
        session=db_session,
        dataset_id=collection_b.dataset_id,
        uri="/data/b1.mcap",
        format_=RecordingFormat.MCAP,
    )

    result = recording_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=collection_a.dataset_id
    )

    assert {recording.recording_id for recording in result} == {recording_id_1, recording_id_2}


def test_get_all_by_dataset_id__empty(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    result = recording_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=collection.dataset_id
    )

    assert result == []
