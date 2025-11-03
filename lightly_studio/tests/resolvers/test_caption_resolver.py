from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.resolvers.caption_resolver import create_many, get_all_captions_by_sample
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


def test_get_all_captions_by_sample(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)

    image_a = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/a.jpg",
    )
    image_b = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/b.jpg",
    )
    image_c = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/c.jpg",
    )

    create_many(
        session=test_db,
        captions=[
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                sample_id=image_a.sample_id,
                text="Caption number 0",
            ),
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                sample_id=image_b.sample_id,
                text="Caption number 1",
            ),
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                sample_id=image_c.sample_id,
                text="Caption number 2",
            ),
        ],
    )

    result_all = get_all_captions_by_sample(session=test_db, dataset_id=dataset.dataset_id)

    assert result_all.total_count == 3
    assert result_all.next_cursor is None

    assert result_all.samples[0].captions[0].text == "Caption number 0"
    assert image_a.sample_id == result_all.samples[0].sample_id

    assert result_all.samples[1].captions[0].text == "Caption number 1"
    assert image_b.sample_id == result_all.samples[1].sample_id

    assert result_all.samples[2].captions[0].text == "Caption number 2"
    assert image_c.sample_id == result_all.samples[2].sample_id

    first_page = get_all_captions_by_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        pagination=Paginated(offset=0, limit=2),
    )

    assert len(first_page.samples) == 2
    assert first_page.total_count == 3
    assert first_page.next_cursor == 2

    assert result_all.samples[0].captions[0].text == "Caption number 0"
    assert image_a.sample_id == result_all.samples[0].sample_id

    assert result_all.samples[1].captions[0].text == "Caption number 1"
    assert image_b.sample_id == result_all.samples[1].sample_id

    second_page = get_all_captions_by_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        pagination=Paginated(offset=2, limit=2),
    )

    assert len(second_page.samples) == 1
    assert second_page.total_count == 3
    assert second_page.next_cursor is None

    assert result_all.samples[2].captions[0].text == "Caption number 2"
    assert image_c.sample_id == result_all.samples[2].sample_id
