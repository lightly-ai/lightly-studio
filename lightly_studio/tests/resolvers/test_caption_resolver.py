from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.resolvers import caption_resolver
from tests.helpers_resolvers import create_dataset, create_image


def test_create_many__returns_empty_when_no_captions(test_db: Session) -> None:
    assert caption_resolver.create_many(session=test_db, captions=[]) == []


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
            parent_sample_id=image_one.sample_id,
            text="hello world",
        ),
        CaptionCreate(
            dataset_id=dataset.dataset_id,
            parent_sample_id=image_one.sample_id,
            text="another hello",
        ),
        CaptionCreate(
            dataset_id=dataset.dataset_id,
            parent_sample_id=image_two.sample_id,
            text="lorem ipsum dolor",
        ),
    ]

    created = caption_resolver.create_many(session=test_db, captions=inputs)

    assert len(created) == 3
    # Check first caption
    assert created[0].dataset_id == dataset.dataset_id
    assert created[0].parent_sample_id == image_one.sample_id
    assert created[0].text == "hello world"

    # Check second caption
    assert created[1].dataset_id == dataset.dataset_id
    assert created[1].parent_sample_id == image_one.sample_id
    assert created[1].text == "another hello"

    # Check third caption
    assert created[2].dataset_id == dataset.dataset_id
    assert created[2].parent_sample_id == image_two.sample_id
    assert created[2].text == "lorem ipsum dolor"

    stored_captions = test_db.exec(select(CaptionTable)).all()
    assert len(stored_captions) == 3


def test_get_all(test_db: Session) -> None:
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

    caption_resolver.create_many(
        session=test_db,
        captions=[
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                parent_sample_id=image_a.sample_id,
                text="first caption",
            ),
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                parent_sample_id=image_b.sample_id,
                text="second caption",
            ),
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                parent_sample_id=image_c.sample_id,
                text="third caption",
            ),
        ],
    )

    # Get all without pagination
    result_all = caption_resolver.get_all(session=test_db, dataset_id=dataset.dataset_id)
    assert result_all.total_count == 3
    assert {caption.parent_sample_id for caption in result_all.captions} == {
        image_a.sample_id,
        image_b.sample_id,
        image_c.sample_id,
    }
    assert result_all.next_cursor is None

    # Get two with pagination and then one with too large pagination
    first_page = caption_resolver.get_all(
        session=test_db,
        dataset_id=dataset.dataset_id,
        pagination=Paginated(offset=0, limit=2),
    )
    assert len(first_page.captions) == 2
    assert first_page.total_count == 3
    assert first_page.next_cursor == 2
    assert {caption.parent_sample_id for caption in first_page.captions} == {
        image_a.sample_id,
        image_b.sample_id,
    }

    second_page = caption_resolver.get_all(
        session=test_db,
        dataset_id=dataset.dataset_id,
        pagination=Paginated(offset=2, limit=2),
    )
    assert len(second_page.captions) == 1
    assert second_page.total_count == 3
    assert second_page.next_cursor is None
    assert {caption.parent_sample_id for caption in second_page.captions} == {
        image_c.sample_id,
    }


def test_get_by_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)

    image_a = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/a.jpg",
    )

    created_captions = caption_resolver.create_many(
        session=test_db,
        captions=[
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                parent_sample_id=image_a.sample_id,
                text="first caption",
            ),
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                parent_sample_id=image_a.sample_id,
                text="second caption",
            ),
        ],
    )

    first_caption_id = created_captions[0].caption_id
    second_caption_id = created_captions[1].caption_id

    # Retrieve 0
    caption_retrieved = caption_resolver.get_by_ids(session=test_db, caption_ids=[])
    assert len(caption_retrieved) == 0

    # Retrieve 1
    caption_retrieved = caption_resolver.get_by_ids(session=test_db, caption_ids=[first_caption_id])
    assert len(caption_retrieved) == 1
    assert caption_retrieved[0].caption_id == first_caption_id

    # Retrieve many
    caption_retrieved = caption_resolver.get_by_ids(
        session=test_db, caption_ids=[first_caption_id, second_caption_id]
    )
    assert len(caption_retrieved) == 2
    assert caption_retrieved[0].caption_id == first_caption_id
    assert caption_retrieved[1].caption_id == second_caption_id


def test_update_text(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)

    image_a = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/a.jpg",
    )

    created_captions = caption_resolver.create_many(
        session=test_db,
        captions=[
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                parent_sample_id=image_a.sample_id,
                text="first caption",
            ),
        ],
    )

    # Update the text and double check it got updated
    caption_updated = caption_resolver.update_text(
        session=test_db, caption_id=created_captions[0].caption_id, text="Updated text"
    )
    assert caption_updated.text == "Updated text"
    caption_retrieved = caption_resolver.get_by_ids(
        session=test_db, caption_ids=[created_captions[0].caption_id]
    )
    assert caption_retrieved[0].text == "Updated text"

    # Try to update non exist caption
    wrong_id = uuid4()
    with pytest.raises(ValueError, match=f"Caption with ID {wrong_id} not found."):
        caption_updated = caption_resolver.update_text(
            session=test_db, caption_id=wrong_id, text="Updated text"
        )


def test_delete_caption(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)

    image_a = create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/samples/a.jpg",
    )

    _ = caption_resolver.create_many(
        session=test_db,
        captions=[
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                parent_sample_id=image_a.sample_id,
                text="first caption",
            ),
            CaptionCreate(
                dataset_id=dataset.dataset_id,
                parent_sample_id=image_a.sample_id,
                text="second caption",
            ),
        ],
    )

    # Assert that we have two captions
    result_all = caption_resolver.get_all(session=test_db, dataset_id=dataset.dataset_id)
    assert len(result_all.captions) == 2

    # Delete the first caption
    caption_resolver.delete_caption(session=test_db, caption_id=result_all.captions[0].caption_id)

    # Assert that only second caption is left
    result_all_new = caption_resolver.get_all(session=test_db, dataset_id=dataset.dataset_id)
    assert len(result_all_new.captions) == 1
    assert result_all_new.captions[0].caption_id == result_all.captions[1].caption_id

    # Try to delete non exist caption
    wrong_id = uuid4()
    with pytest.raises(ValueError, match=f"Caption with ID {wrong_id} not found."):
        caption_resolver.delete_caption(session=test_db, caption_id=wrong_id)
