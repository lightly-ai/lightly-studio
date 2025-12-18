from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session, select

from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import caption_resolver, collection_resolver
from tests.helpers_resolvers import create_collection, create_image


def test_create_many__returns_empty_when_no_captions(test_db: Session) -> None:
    dataset_id = create_collection(session=test_db).collection_id
    assert (
        caption_resolver.create_many(session=test_db, parent_collection_id=dataset_id, captions=[])
        == []
    )


def test_create_many(test_db: Session) -> None:
    dataset = create_collection(session=test_db)
    image_one = create_image(
        session=test_db,
        collection_id=dataset.collection_id,
        file_path_abs="/samples/sample_one.jpg",
    )
    image_two = create_image(
        session=test_db,
        collection_id=dataset.collection_id,
        file_path_abs="/samples/sample_two.jpg",
    )

    inputs = [
        CaptionCreate(
            parent_sample_id=image_one.sample_id,
            text="hello world",
        ),
        CaptionCreate(
            parent_sample_id=image_one.sample_id,
            text="another hello",
        ),
        CaptionCreate(
            parent_sample_id=image_two.sample_id,
            text="lorem ipsum dolor",
        ),
    ]

    created_ids = caption_resolver.create_many(
        session=test_db, parent_collection_id=dataset.collection_id, captions=inputs
    )
    created = caption_resolver.get_by_ids(session=test_db, sample_ids=created_ids)

    assert len(created) == 3
    # Check first caption
    assert created[0].parent_sample.collection_id == dataset.collection_id
    assert created[0].parent_sample_id == image_one.sample_id
    assert created[0].text == "hello world"

    # Check second caption
    assert created[1].parent_sample.collection_id == dataset.collection_id
    assert created[1].parent_sample_id == image_one.sample_id
    assert created[1].text == "another hello"

    # Check third caption
    assert created[2].parent_sample.collection_id == dataset.collection_id
    assert created[2].parent_sample_id == image_two.sample_id
    assert created[2].text == "lorem ipsum dolor"

    stored_captions = test_db.exec(select(CaptionTable)).all()
    assert len(stored_captions) == 3


def test_create_many__check_dataset_ids(test_db: Session) -> None:
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id
    image = create_image(session=test_db, collection_id=dataset_id)

    created_ids = caption_resolver.create_many(
        session=test_db,
        parent_collection_id=dataset_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="hello world",
            ),
        ],
    )
    created = caption_resolver.get_by_ids(session=test_db, sample_ids=created_ids)[0]

    expected_caption_dataset_id = collection_resolver.get_or_create_child_collection(
        session=test_db, collection_id=dataset_id, sample_type=SampleType.CAPTION
    )
    assert created.sample.collection_id == expected_caption_dataset_id
    assert created.parent_sample.collection_id == dataset_id


def test_create_many__relationships(test_db: Session) -> None:
    dataset = create_collection(session=test_db)
    dataset_id = dataset.collection_id
    image = create_image(session=test_db, collection_id=dataset_id)

    created_ids = caption_resolver.create_many(
        session=test_db,
        parent_collection_id=dataset_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="hello world",
            ),
        ],
    )
    created = caption_resolver.get_by_ids(session=test_db, sample_ids=created_ids)[0]
    caption_sample = created.sample
    parent_sample = created.parent_sample

    # Caption relationships
    assert caption_sample.sample_id == created.sample_id
    assert parent_sample.sample_id == image.sample_id

    # Parent sample captions relationship
    assert len(parent_sample.captions) == 1
    assert parent_sample.captions[0].sample_id == created.sample_id

    # Caption's sample captions relationships
    assert caption_sample.captions == []


def test_get_by_id(test_db: Session) -> None:
    dataset = create_collection(session=test_db)

    image_a = create_image(
        session=test_db,
        collection_id=dataset.collection_id,
        file_path_abs="/samples/a.jpg",
    )

    created_caption_ids = caption_resolver.create_many(
        session=test_db,
        parent_collection_id=dataset.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image_a.sample_id,
                text="first caption",
            ),
            CaptionCreate(
                parent_sample_id=image_a.sample_id,
                text="second caption",
            ),
        ],
    )

    # Retrieve 0
    caption_retrieved = caption_resolver.get_by_ids(session=test_db, sample_ids=[])
    assert len(caption_retrieved) == 0

    # Retrieve 1
    caption_retrieved = caption_resolver.get_by_ids(
        session=test_db, sample_ids=[created_caption_ids[0]]
    )
    assert len(caption_retrieved) == 1
    assert caption_retrieved[0].sample_id == created_caption_ids[0]

    # Retrieve many
    caption_retrieved = caption_resolver.get_by_ids(
        session=test_db, sample_ids=[created_caption_ids[0], created_caption_ids[1]]
    )
    assert len(caption_retrieved) == 2
    assert caption_retrieved[0].sample_id == created_caption_ids[0]
    assert caption_retrieved[1].sample_id == created_caption_ids[1]


def test_update_text(test_db: Session) -> None:
    dataset = create_collection(session=test_db)

    image_a = create_image(
        session=test_db,
        collection_id=dataset.collection_id,
        file_path_abs="/samples/a.jpg",
    )

    created_caption_ids = caption_resolver.create_many(
        session=test_db,
        parent_collection_id=dataset.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image_a.sample_id,
                text="first caption",
            ),
        ],
    )

    # Update the text and double check it got updated
    caption_updated = caption_resolver.update_text(
        session=test_db, sample_id=created_caption_ids[0], text="Updated text"
    )
    assert caption_updated.text == "Updated text"
    caption_retrieved = caption_resolver.get_by_ids(
        session=test_db, sample_ids=[created_caption_ids[0]]
    )
    assert caption_retrieved[0].text == "Updated text"

    # Try to update non exist caption
    wrong_id = uuid4()
    with pytest.raises(ValueError, match=f"Caption with ID {wrong_id} not found."):
        caption_updated = caption_resolver.update_text(
            session=test_db, sample_id=wrong_id, text="Updated text"
        )


def test_delete_caption(test_db: Session) -> None:
    dataset = create_collection(session=test_db)

    image = create_image(
        session=test_db,
        collection_id=dataset.collection_id,
        file_path_abs="/samples/a.jpg",
    )

    caption_ids = caption_resolver.create_many(
        session=test_db,
        parent_collection_id=dataset.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="first caption",
            ),
            CaptionCreate(
                parent_sample_id=image.sample_id,
                text="second caption",
            ),
        ],
    )

    # Assert that we have two captions
    assert len(image.sample.captions) == 2

    # Delete the first caption
    caption_resolver.delete_caption(session=test_db, sample_id=caption_ids[0])

    # Assert that only second caption is left
    assert len(image.sample.captions) == 1
    assert image.sample.captions[0].sample_id == caption_ids[1]

    # Try to delete a non-existing caption
    wrong_id = uuid4()
    with pytest.raises(ValueError, match=f"Caption with ID {wrong_id} not found."):
        caption_resolver.delete_caption(session=test_db, sample_id=wrong_id)
