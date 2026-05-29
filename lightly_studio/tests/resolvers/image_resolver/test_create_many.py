import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import image_resolver
from lightly_studio.utils import batching
from tests.helpers_resolvers import create_collection


def test_create_many_samples(db_session: Session) -> None:
    """Test bulk creation of samples."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Use out of order file names to verify that order is preserved
    samples_to_create = [
        ImageCreate(
            file_path_abs="/path/to/image_1.png",
            file_name="image_1.png",
            width=100,
            height=200,
        ),
        ImageCreate(
            file_path_abs="/path/to/image_0.png",
            file_name="image_0.png",
            width=300,
            height=400,
        ),
    ]

    created_sample_ids = image_resolver.create_many(
        session=db_session, collection_id=collection_id, samples=samples_to_create
    )
    retrieved_samples = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, sample_ids=created_sample_ids
    ).samples

    # Retrieved samples are ordered by path
    assert len(retrieved_samples) == 2
    assert retrieved_samples[0].file_name == "image_0.png"
    assert retrieved_samples[1].file_name == "image_1.png"

    # Created_sample_ids should preserve the order of input samples
    assert len(created_sample_ids) == 2
    assert created_sample_ids[0] == retrieved_samples[1].sample_id
    assert created_sample_ids[1] == retrieved_samples[0].sample_id

    # Check other fields
    assert retrieved_samples[0].file_path_abs == "/path/to/image_0.png"
    assert retrieved_samples[0].file_name == "image_0.png"
    assert retrieved_samples[0].width == 300
    assert retrieved_samples[0].height == 400
    assert retrieved_samples[0].sample.collection_id == collection_id


def test_create_many_samples__preserves_order_across_batches(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returned ids stay aligned with the input order when the insert spans batches."""
    # Force a tiny insert batch so 5 samples are inserted across 3 statements.
    monkeypatch.setattr(batching, "DEFAULT_BATCH_SIZE", 2)
    collection_id = create_collection(session=db_session).collection_id

    samples_to_create = [
        ImageCreate(
            file_path_abs=f"/path/to/image_{i}.png",
            file_name=f"image_{i}.png",
            width=100 + i,
            height=200 + i,
        )
        for i in range(5)
    ]

    created_sample_ids = image_resolver.create_many(
        session=db_session, collection_id=collection_id, samples=samples_to_create
    )

    # No ids dropped or duplicated across batch boundaries.
    assert len(created_sample_ids) == 5
    assert len(set(created_sample_ids)) == 5
    # Each returned id maps back to its positionally-matching input sample.
    for sample_id, sample_in in zip(created_sample_ids, samples_to_create):
        image = image_resolver.get_by_id(session=db_session, sample_id=sample_id)
        assert image is not None
        assert image.file_name == sample_in.file_name


def test_create_many__sample_type_mismatch(db_session: Session) -> None:
    """Test bulk creation of samples."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    with pytest.raises(ValueError, match="is having sample type 'video', expected 'image'"):
        image_resolver.create_many(
            session=db_session,
            collection_id=collection.collection_id,
            samples=[
                ImageCreate(
                    file_path_abs="/path/to/sample1.png",
                    file_name="sample1.png",
                    width=100,
                    height=200,
                ),
            ],
        )
