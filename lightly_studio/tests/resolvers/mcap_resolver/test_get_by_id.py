import uuid

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import mcap_resolver
from tests.helpers_resolvers import create_collection, create_mcap


def test_get_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
    mcap = create_mcap(session=db_session, collection_id=collection.collection_id, channel_id=3)

    result = mcap_resolver.get_by_id(session=db_session, sample_id=mcap.sample_id)

    assert result is not None
    assert result.sample_id == mcap.sample_id
    assert result.channel_id == 3


def test_get_by_id__nonexistent(db_session: Session) -> None:
    result = mcap_resolver.get_by_id(session=db_session, sample_id=uuid.uuid4())

    assert result is None
