from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.resolvers.caption_resolver import create_many, get_all
from tests.helpers_resolvers import create_dataset, create_sample


def test_create_many__returns_empty_when_no_captions(test_db: Session) -> None:
    assert create_many(session=test_db, captions=[]) == []


def test_create_many(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    sample_one = create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/sample_one.jpg",
    )
    sample_two = create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/sample_two.jpg",
    )

    inputs = [
        CaptionCreate(
            dataset_id=dataset.dataset_id,
            sample_id=sample_one.sample_id,
            text="hello world",
        ),
        CaptionCreate(
            dataset_id=dataset.dataset_id,
            sample_id=sample_one.sample_id,
            text="another hello",
        ),
        CaptionCreate(
            dataset_id=dataset.dataset_id,
            sample_id=sample_two.sample_id,
            text="lorem ipsum dolor",
        ),
    ]

    created = create_many(session=test_db, captions=inputs)

    assert len(created) == 3
    # Check first caption
    assert created[0].dataset_id == dataset.dataset_id
    assert created[0].sample_id == sample_one.sample_id
    assert created[0].text == "hello world"

    # Check second caption
    assert created[1].dataset_id == dataset.dataset_id
    assert created[1].sample_id == sample_one.sample_id
    assert created[1].text == "another hello"

    # Check third caption
    assert created[2].dataset_id == dataset.dataset_id
    assert created[2].sample_id == sample_two.sample_id
    assert created[2].text == "lorem ipsum dolor"

    stored_captions = test_db.exec(select(CaptionTable)).all()
    assert len(stored_captions) == 3


def test_get_all(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)

    sample_a = create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/a.jpg",
    )
    sample_b = create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/b.jpg",
    )
    sample_c = create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/c.jpg",
    )

    create_many(
        session=test_db,
        captions=[
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                sample_id=sample_a.sample_id,
                text="first caption",
            ),
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                sample_id=sample_b.sample_id,
                text="second caption",
            ),
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                sample_id=sample_c.sample_id,
                text="third caption",
            ),
        ],
    )

    # Get all without pagination
    result_all = get_all(session=test_db, dataset_id=dataset.dataset_id)
    assert result_all.total_count == 3
    assert {caption.sample_id for caption in result_all.captions} == {
        sample_a.sample_id,
        sample_b.sample_id,
        sample_c.sample_id,
    }
    assert result_all.next_cursor is None

    # Get two with pagination and then one with too large pagination
    first_page = get_all(
        session=test_db,
        dataset_id=dataset.dataset_id,
        pagination=Paginated(offset=0, limit=2),
    )
    assert len(first_page.captions) == 2
    assert first_page.total_count == 3
    assert first_page.next_cursor == 2
    assert {caption.sample_id for caption in first_page.captions} == {
        sample_a.sample_id,
        sample_b.sample_id,
    }

    second_page = get_all(
        session=test_db,
        dataset_id=dataset.dataset_id,
        pagination=Paginated(offset=2, limit=2),
    )
    assert len(second_page.captions) == 1
    assert second_page.total_count == 3
    assert second_page.next_cursor is None
    assert {caption.sample_id for caption in second_page.captions} == {
        sample_c.sample_id,
    }
