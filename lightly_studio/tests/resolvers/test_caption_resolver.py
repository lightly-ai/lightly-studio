from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.resolvers.caption_resolver import create_many
from tests.helpers_resolvers import create_dataset, create_image


def test_create_many__returns_empty_when_no_captions(test_db: Session) -> None:
    assert create_many(session=test_db, captions=[]) == []


def test_create_many(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    image_one = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/sample_one.jpg",
    )
    image_two = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/sample_two.jpg",
    )

    inputs = [
        CaptionCreate(
            dataset_id=dataset.dataset_id,
            sample_id=image_one.sample_id,
            text="hello world",
        ),
        CaptionCreate(
            dataset_id=dataset.dataset_id,
            sample_id=image_one.sample_id,
            text="another hello",
        ),
        CaptionCreate(
            dataset_id=dataset.dataset_id,
            sample_id=image_two.sample_id,
            text="lorem ipsum dolor",
        ),
    ]

    created = create_many(session=test_db, captions=inputs)

    assert len(created) == 3
    # Check first caption
    assert created[0].dataset_id == dataset.dataset_id
    assert created[0].sample_id == image_one.sample_id
    assert created[0].text == "hello world"

    # Check second caption
    assert created[1].dataset_id == dataset.dataset_id
    assert created[1].sample_id == image_one.sample_id
    assert created[1].text == "another hello"

    # Check third caption
    assert created[2].dataset_id == dataset.dataset_id
    assert created[2].sample_id == image_two.sample_id
    assert created[2].text == "lorem ipsum dolor"

    stored_captions = test_db.exec(select(CaptionTable)).all()
    assert len(stored_captions) == 3
