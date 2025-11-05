from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver
from lightly_studio.resolvers.caption_resolver import create_many
from lightly_studio.resolvers.sample_resolver import get_all_samples_with_captions
from tests.helpers_resolvers import create_dataset, create_image


def test_create_and_get_by_id(db_session: Session) -> None:
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.dataset_id

    create = SampleCreate(dataset_id=dataset_id)
    sample = sample_resolver.create(session=db_session, sample=create)
    assert sample.dataset_id == dataset_id

    fetched_sample = sample_resolver.get_by_id(session=db_session, sample_id=sample.sample_id)
    assert fetched_sample is not None
    assert fetched_sample.sample_id == sample.sample_id
    assert fetched_sample.dataset_id == dataset_id


def test_create_many_and_get_many_by_id(db_session: Session) -> None:
    dataset1 = create_dataset(session=db_session)
    dataset1_id = dataset1.dataset_id
    dataset2 = create_dataset(session=db_session, dataset_name="dataset2")
    dataset2_id = dataset2.dataset_id

    creates = [
        SampleCreate(dataset_id=dataset1_id),
        SampleCreate(dataset_id=dataset2_id),
        SampleCreate(dataset_id=dataset1_id),
    ]
    sample_ids = sample_resolver.create_many(session=db_session, samples=creates)
    assert len(sample_ids) == 3

    fetched_samples = sample_resolver.get_many_by_id(session=db_session, sample_ids=sample_ids)
    assert len(fetched_samples) == 3
    assert fetched_samples[0].sample_id == sample_ids[0]
    assert fetched_samples[0].dataset_id == dataset1_id
    assert fetched_samples[1].sample_id == sample_ids[1]
    assert fetched_samples[1].dataset_id == dataset2_id
    assert fetched_samples[2].sample_id == sample_ids[2]
    assert fetched_samples[2].dataset_id == dataset1_id


def test_get_all_samples_with_captions(test_db: Session) -> None:
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

    result_all = get_all_samples_with_captions(session=test_db, dataset_id=dataset.dataset_id)

    assert result_all.total_count == 3
    assert result_all.next_cursor is None

    assert result_all.samples[0].captions[0].text == "Caption number 0"
    assert image_a.sample_id == result_all.samples[0].sample_id

    assert result_all.samples[1].captions[0].text == "Caption number 1"
    assert image_b.sample_id == result_all.samples[1].sample_id

    assert result_all.samples[2].captions[0].text == "Caption number 2"
    assert image_c.sample_id == result_all.samples[2].sample_id

    first_page = get_all_samples_with_captions(
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

    second_page = get_all_samples_with_captions(
        session=test_db,
        dataset_id=dataset.dataset_id,
        pagination=Paginated(offset=2, limit=2),
    )

    assert len(second_page.samples) == 1
    assert second_page.total_count == 3
    assert second_page.next_cursor is None

    assert result_all.samples[2].captions[0].text == "Caption number 2"
    assert image_c.sample_id == result_all.samples[2].sample_id
