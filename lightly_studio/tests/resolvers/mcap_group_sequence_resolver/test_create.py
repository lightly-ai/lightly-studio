"""Tests for creating MCAP group sequences."""

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.resolvers import mcap_group_sequence_resolver, sample_resolver
from tests.helpers_resolvers import create_collection


def test_create(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    sample_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        mcap_path="/bags/drive_001.mcap",
    )

    sequence = db_session.get(SequenceTable, sample_id)
    assert sequence is not None
    row = mcap_group_sequence_resolver.get_by_id(session=db_session, sample_id=sample_id)
    assert row is not None
    assert row.sample_id == sample_id
    assert row.mcap_path == "/bags/drive_001.mcap"
    sample = sample_resolver.get_by_id(session=db_session, sample_id=sample_id)
    assert sample is not None
    assert sample.collection_id == collection.collection_id


def test_create__missing_collection(db_session: Session) -> None:
    with pytest.raises(ValueError, match=r"Collection with id .* not found"):
        mcap_group_sequence_resolver.create(
            session=db_session,
            collection_id=uuid.uuid4(),
            mcap_path="/bags/drive_001.mcap",
        )


def test_create__non_sequence_collection(db_session: Session) -> None:
    image_col = create_collection(session=db_session, sample_type=SampleType.IMAGE)

    with pytest.raises(ValueError, match="is having sample type 'image', expected 'sequence'"):
        mcap_group_sequence_resolver.create(
            session=db_session,
            collection_id=image_col.collection_id,
            mcap_path="/bags/drive_001.mcap",
        )


@pytest.mark.parametrize("mcap_path", ["", "   "])
def test_create__empty_path(db_session: Session, mcap_path: str) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    with pytest.raises(ValueError, match="mcap_path must be non-empty"):
        mcap_group_sequence_resolver.create(
            session=db_session,
            collection_id=collection.collection_id,
            mcap_path=mcap_path,
        )


@pytest.mark.parametrize("mcap_path", ["/bags/drive_001.bag", "/bags/drive_001", "drive.mcap.bak"])
def test_create__invalid_extension(db_session: Session, mcap_path: str) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    with pytest.raises(ValueError, match=r"mcap_path must end with '\.mcap'"):
        mcap_group_sequence_resolver.create(
            session=db_session,
            collection_id=collection.collection_id,
            mcap_path=mcap_path,
        )
