"""Tests for reading a sequence's recording and MCAP component schema."""

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.resolvers import mcap_group_sequence_resolver, sample_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.mcap_group_sequence_resolver.helpers import create_mcap_sequence


def test_get_info(db_session: Session) -> None:
    fixture = create_mcap_sequence(session=db_session, uri="/bags/drive_001.mcap")

    info = mcap_group_sequence_resolver.get_info(session=db_session, sample_id=fixture.sample_id)

    assert info is not None
    assert info.sample_id == fixture.sample_id
    assert info.recording.recording_id == fixture.recording_id
    assert info.recording.uri == "/bags/drive_001.mcap"
    assert info.recording.dataset_id == fixture.sequence_collection.dataset_id

    assert [component.group_component_name for component in info.components] == [
        "front",
        "pcl_front",
    ]
    front, pcl_front = info.components
    assert front.collection_id == fixture.slots["front"].collection_id
    assert front.group_component_index == 0
    assert front.mcap_data_type == McapDataType.VIDEO_FRAME
    assert front.channel_id == 3
    assert front.frame_id == "main"
    assert pcl_front.collection_id == fixture.slots["pcl_front"].collection_id
    assert pcl_front.group_component_index == 1
    assert pcl_front.mcap_data_type == McapDataType.POINT_CLOUD
    assert pcl_front.channel_id == 7
    assert pcl_front.frame_id == "livox_front_left"


def test_get_info__classic_sequence(db_session: Session) -> None:
    """A sequence with no `mcap_group_sequence` row is a classic sequence."""
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)
    sample_id = sample_resolver.create_many(
        session=db_session, samples=[SampleCreate(collection_id=collection.collection_id)]
    )[0]
    db_session.bulk_save_objects(objects=[SequenceTable(sample_id=sample_id)])
    db_session.commit()

    info = mcap_group_sequence_resolver.get_info(session=db_session, sample_id=sample_id)

    assert info is None


def test_get_info__missing_sequence(db_session: Session) -> None:
    with pytest.raises(ValueError, match=r"Sequence with sample_id .* does not exist"):
        mcap_group_sequence_resolver.get_info(session=db_session, sample_id=uuid.uuid4())


def test_get_info__empty_sequence_still_has_slots(db_session: Session) -> None:
    """The schema is returned even when no ticks have been indexed yet."""
    fixture = create_mcap_sequence(session=db_session)

    info = mcap_group_sequence_resolver.get_info(session=db_session, sample_id=fixture.sample_id)

    assert info is not None
    assert len(info.components) == 2


def test_get_info__does_not_include_classic_image_slots(db_session: Session) -> None:
    """A non-MCAP child of the GROUP collection is not a component and is omitted."""
    fixture = create_mcap_sequence(
        session=db_session, extra_slots=[("thumbnail", SampleType.IMAGE)]
    )

    info = mcap_group_sequence_resolver.get_info(session=db_session, sample_id=fixture.sample_id)

    assert info is not None
    assert [component.group_component_name for component in info.components] == [
        "front",
        "pcl_front",
    ]
