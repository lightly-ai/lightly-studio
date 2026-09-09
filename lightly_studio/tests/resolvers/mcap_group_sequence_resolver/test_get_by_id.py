"""Tests for reading MCAP group sequences."""

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.resolvers import mcap_group_sequence_resolver, sample_resolver
from tests.helpers_resolvers import create_collection


def test_get_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    sample_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        mcap_path="/bags/drive_001.mcap",
    )

    row = mcap_group_sequence_resolver.get_by_id(session=db_session, sample_id=sample_id)

    assert row is not None
    assert row.sample_id == sample_id
    assert row.mcap_path == "/bags/drive_001.mcap"


def test_get_by_id__classic_sequence(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    sample_ids = sample_resolver.create_many(
        session=db_session,
        samples=[SampleCreate(collection_id=collection.collection_id)],
    )
    db_session.add(SequenceTable(sample_id=sample_ids[0]))
    db_session.commit()

    row = mcap_group_sequence_resolver.get_by_id(session=db_session, sample_id=sample_ids[0])
    assert row is None
