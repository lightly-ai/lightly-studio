from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_collection, create_image, create_tag


def test_split__partitions_the_current_filtered_query(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    narrow = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="narrow.png",
        width=10,
    )
    wide_images = [
        create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs=f"wide-{index}.png",
            width=100,
        )
        for index in range(3)
    ]

    counts = (
        DatasetQuery(dataset=dataset, session=db_session)
        .match(ImageSampleField.width > 50)
        .split({"train": 2, "test": 1}, seed=7)
    )

    assert counts == {"train": 2, "test": 1}
    tagged_sample_ids = set()
    for tag_name in counts:
        tag = tag_resolver.get_by_name(
            session=db_session, tag_name=tag_name, collection_id=dataset.collection_id
        )
        assert tag is not None
        tagged_sample_ids.update(
            tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id)
        )
    assert tagged_sample_ids == {image.sample_id for image in wide_images}
    assert narrow.sample_id not in tagged_sample_ids


@pytest.mark.parametrize(
    "tag_sizes",
    [
        {"train": 1},
        {" ": 1, "test": 1},
        {" train ": 1, "train": 1},
        {"train": 0, "test": 1},
        {"train": -1, "test": 1},
    ],
)
def test_split__rejects_invalid_tag_sizes(db_session: Session, tag_sizes: dict[str, int]) -> None:
    dataset = create_collection(session=db_session)
    create_image(session=db_session, collection_id=dataset.collection_id)
    create_image(session=db_session, collection_id=dataset.collection_id)

    with pytest.raises(ValueError, match=r"At least|must"):
        DatasetQuery(dataset=dataset, session=db_session).split(tag_sizes=tag_sizes)


def test_split__rejects_empty_or_too_small_query_result(db_session: Session) -> None:
    dataset = create_collection(session=db_session)

    with pytest.raises(ValueError, match="empty"):
        DatasetQuery(dataset=dataset, session=db_session).split(tag_sizes={"train": 1, "test": 1})

    create_image(session=db_session, collection_id=dataset.collection_id)
    with pytest.raises(ValueError, match="cannot exceed"):
        DatasetQuery(dataset=dataset, session=db_session).split(
            tag_sizes={"train": 1, "validation": 1, "test": 1}
        )


def test_split__rejects_existing_tag_without_creating_other_tags(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    create_image(session=db_session, collection_id=dataset.collection_id)
    create_image(session=db_session, collection_id=dataset.collection_id)
    create_tag(
        session=db_session,
        collection_id=dataset.collection_id,
        tag_name="train",
    )

    with pytest.raises(ValueError, match="already exist"):
        DatasetQuery(dataset=dataset, session=db_session).split(tag_sizes={"train": 1, "test": 1})

    assert (
        tag_resolver.get_by_name(
            session=db_session, tag_name="test", collection_id=dataset.collection_id
        )
        is None
    )


def test_split__same_seed_assigns_the_same_samples(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    for index in range(8):
        create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs=f"s{index}.png",
        )

    # Splitting twice with the same seed must tag the same samples, so the two "train" tags
    # hold identical sets even though the resolver shuffles the scope.
    tagged_sample_ids = []
    for prefix in ("first", "second"):
        DatasetQuery(dataset=dataset, session=db_session).split(
            {f"{prefix}-train": 1, f"{prefix}-test": 1}, seed=7
        )
        tag = tag_resolver.get_by_name(
            session=db_session,
            tag_name=f"{prefix}-train",
            collection_id=dataset.collection_id,
        )
        assert tag is not None
        tagged_sample_ids.append(
            set(tag_resolver.get_sample_ids_by_tag_id(session=db_session, tag_id=tag.tag_id))
        )

    assert tagged_sample_ids[0] == tagged_sample_ids[1]


def test_split__rejects_unsupported_sample_type(db_session: Session) -> None:
    dataset = create_collection(session=db_session, sample_type=SampleType.VIDEO_FRAME)

    with pytest.raises(ValueError, match="only supported for image and video"):
        DatasetQuery(dataset=dataset, session=db_session).split(tag_sizes={"train": 1, "test": 1})
