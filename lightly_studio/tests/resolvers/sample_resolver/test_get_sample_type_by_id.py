"""Tests for get_sample_type resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_collection


def test_get_sample_type_by_id(db_session: Session) -> None:
    """Test getting sample type by sample_id."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    create = SampleCreate(collection_id=collection_id)
    sample = sample_resolver.create(session=db_session, sample=create)

    sample_type = sample_resolver.get_sample_type_by_id(
        session=db_session, sample_id=sample.sample_id
    )
    assert sample_type == SampleType.IMAGE


def test_get_sample_type_by_id_video(db_session: Session) -> None:
    """Test getting sample type for video sample."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    create = SampleCreate(collection_id=collection_id)
    sample = sample_resolver.create(session=db_session, sample=create)

    sample_type = sample_resolver.get_sample_type_by_id(
        session=db_session, sample_id=sample.sample_id
    )
    assert sample_type == SampleType.VIDEO


def test_get_sample_type_by_id_group(db_session: Session) -> None:
    """Test getting sample type for group sample."""
    collection = create_collection(session=db_session, sample_type=SampleType.GROUP)
    collection_id = collection.collection_id

    create = SampleCreate(collection_id=collection_id)
    sample = sample_resolver.create(session=db_session, sample=create)

    sample_type = sample_resolver.get_sample_type_by_id(
        session=db_session, sample_id=sample.sample_id
    )
    assert sample_type == SampleType.GROUP


def test_get_sample_type_by_id_nonexistent(db_session: Session) -> None:
    """Test getting sample type for non-existent sample raises ValueError."""
    import uuid

    non_existent_id = uuid.uuid4()
    with pytest.raises(ValueError, match="does not exist"):
        sample_resolver.get_sample_type_by_id(session=db_session, sample_id=non_existent_id)
