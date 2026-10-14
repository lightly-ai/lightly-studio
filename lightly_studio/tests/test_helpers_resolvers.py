"""Tests for shared resolver test helpers."""

from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import create_collection, create_image_with_metadata


def test_create_image_with_metadata(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    sample = create_image_with_metadata(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/front.png",
        width=640,
        height=480,
        metadata={
            "camera": "front",
            "score": 15,
            "reviewed": True,
            "odometry": {"acc": [20, 10]},
            "missing": None,
        },
    )

    assert isinstance(sample, ImageSample)
    assert sample.file_path_abs == "/images/front.png"
    assert sample.file_name == "front.png"
    assert sample.width == 640
    assert sample.height == 480
    assert sample.collection_id == collection_id

    sample_id = sample.sample_id
    db_session.expunge_all()
    image_table = image_resolver.get_by_id(session=db_session, sample_id=sample_id)
    assert image_table is not None
    reloaded = ImageSample(inner=image_table)
    assert reloaded.metadata["camera"] == "front"
    assert reloaded.metadata["score"] == 15
    assert reloaded.metadata["reviewed"] is True
    assert reloaded.metadata["odometry"] == {"acc": [20, 10]}
    assert reloaded.metadata["missing"] is None
