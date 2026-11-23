"""Tests for recording_resolver.set_reference_frame_ids."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import recording_resolver
from tests.helpers_resolvers import create_collection


def test_set_reference_frame_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    recording_id = recording_resolver.create(
        session=db_session,
        dataset_id=collection.dataset_id,
        uri="/data/recording.mcap",
        format_=RecordingFormat.MCAP,
    )

    recording_resolver.set_reference_frame_ids(
        session=db_session, recording_id=recording_id, frame_ids=["map", "base_link"]
    )

    result = recording_resolver.get_by_id(session=db_session, recording_id=recording_id)
    assert result is not None
    assert result.reference_frame_ids == ["map", "base_link"]


def test_set_reference_frame_ids__missing(db_session: Session) -> None:
    with pytest.raises(ValueError, match="not found"):
        recording_resolver.set_reference_frame_ids(
            session=db_session, recording_id=uuid4(), frame_ids=["map"]
        )
