from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query import random_split
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images


class TestValidateSizes:
    def test_validate_sizes__valid(self) -> None:
        random_split.validate_sizes({"train": 80, "val": 10, "test": 10})

    def test_validate_sizes__empty(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            random_split.validate_sizes({})

    def test_validate_sizes__non_positive(self) -> None:
        with pytest.raises(ValueError, match="greater than 0"):
            random_split.validate_sizes({"train": 100, "val": 0})

    def test_validate_sizes__empty_name(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            random_split.validate_sizes({"  ": 100})

    def test_validate_sizes__parts_need_not_sum_to_100(self) -> None:
        # Sizes are relative parts, so any positive totals are accepted.
        random_split.validate_sizes({"train": 8, "val": 1, "test": 1})
        random_split.validate_sizes({"train": 3, "val": 1})


class TestPartitionCounts:
    def test_partition_counts__exact(self) -> None:
        counts = random_split.partition_counts(
            total=1000, sizes={"train": 80, "val": 10, "test": 10}
        )
        assert counts == {"train": 800, "val": 100, "test": 100}

    def test_partition_counts__largest_remainder(self) -> None:
        # Exact shares are 2.8 / 2.8 / 1.4; the two units of leftover go to the
        # largest remainders (train and val), never to test.
        counts = random_split.partition_counts(total=7, sizes={"train": 40, "val": 40, "test": 20})
        assert counts == {"train": 3, "val": 3, "test": 1}

    def test_partition_counts__sums_to_total(self) -> None:
        counts = random_split.partition_counts(total=17, sizes={"a": 33, "b": 33, "c": 34})
        assert sum(counts.values()) == 17

    def test_partition_counts__zero_total(self) -> None:
        counts = random_split.partition_counts(total=0, sizes={"train": 80, "val": 20})
        assert counts == {"train": 0, "val": 0}

    def test_partition_counts__unnormalized_parts(self) -> None:
        # Parts are normalized by their sum, so 8/1/1 matches 80/10/10.
        counts = random_split.partition_counts(total=1000, sizes={"train": 8, "val": 1, "test": 1})
        assert counts == {"train": 800, "val": 100, "test": 100}


class TestRandomSplit:
    def test_random_split__assigns_each_sample_once(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        images = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path=f"s{i}.png") for i in range(10)],
        )
        sample_ids = [image.sample_id for image in images]

        result = random_split.random_split(
            session=db_session,
            collection_id=collection.collection_id,
            sample_ids=sample_ids,
            sizes={"train": 80, "val": 10, "test": 10},
            seed=42,
        )

        assert result.counts == {"train": 8, "val": 1, "test": 1}
        assert result.seed == 42
        # Every input sample is tagged with exactly one split.
        tagged = _split_tag_names_by_sample(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )
        assert all(len(names) == 1 for names in tagged.values())

    def test_random_split__is_deterministic_for_seed(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        images = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path=f"s{i}.png") for i in range(10)],
        )
        sample_ids = [image.sample_id for image in images]

        first = _run_and_read_train(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )
        second = _run_and_read_train(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )
        assert first == second

    def test_random_split__overwrites_previous_assignment(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        images = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path=f"s{i}.png") for i in range(10)],
        )
        sample_ids = [image.sample_id for image in images]

        random_split.random_split(
            session=db_session,
            collection_id=collection.collection_id,
            sample_ids=sample_ids,
            sizes={"train": 50, "val": 50},
            seed=1,
        )
        random_split.random_split(
            session=db_session,
            collection_id=collection.collection_id,
            sample_ids=sample_ids,
            sizes={"train": 50, "val": 50},
            seed=2,
        )

        # After a re-run each sample is still tagged with exactly one split.
        tagged = _split_tag_names_by_sample(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )
        assert all(len(names) == 1 for names in tagged.values())

    def test_random_split__empty_input_is_noop(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)

        result = random_split.random_split(
            session=db_session,
            collection_id=collection.collection_id,
            sample_ids=[],
            sizes={"train": 80, "val": 20},
            seed=7,
        )

        assert result.counts == {"train": 0, "val": 0}
        # No tags are created for an empty input set.
        assert (
            tag_resolver.get_by_name(
                session=db_session, tag_name="train", collection_id=collection.collection_id
            )
            is None
        )

    def test_random_split__zero_count_split_creates_empty_tag(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        images = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path="s0.png")],
        )
        sample_ids = [image.sample_id for image in images]

        result = random_split.random_split(
            session=db_session,
            collection_id=collection.collection_id,
            sample_ids=sample_ids,
            sizes={"train": 90, "val": 10},
            seed=1,
        )

        assert result.counts == {"train": 1, "val": 0}
        # The empty split still exists as a tag.
        val_tag = tag_resolver.get_by_name(
            session=db_session, tag_name="val", collection_id=collection.collection_id
        )
        assert val_tag is not None

    def test_random_split__invalid_sizes_raises(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        with pytest.raises(ValueError, match="greater than 0"):
            random_split.random_split(
                session=db_session,
                collection_id=collection.collection_id,
                sample_ids=[],
                sizes={"train": 8, "val": 0},
            )


def _run_and_read_train(session: Session, collection_id: UUID, sample_ids: list[UUID]) -> set[UUID]:
    random_split.random_split(
        session=session,
        collection_id=collection_id,
        sample_ids=sample_ids,
        sizes={"train": 60, "val": 40},
        seed=123,
    )
    tag = tag_resolver.get_by_name(session=session, tag_name="train", collection_id=collection_id)
    assert tag is not None
    return set(tag_resolver.get_tags_by_sample(session=session, tag_ids=[tag.tag_id]).keys())


def _split_tag_names_by_sample(
    session: Session, collection_id: UUID, sample_ids: list[UUID]
) -> dict[UUID, set[str]]:
    """Return, for each input sample, the set of split tag names linked to it."""
    tag_ids = []
    for name in ("train", "val", "test"):
        tag = tag_resolver.get_by_name(session=session, tag_name=name, collection_id=collection_id)
        if tag is not None:
            tag_ids.append(tag.tag_id)
    names_by_id = tag_resolver.get_names_by_ids(session=session, tag_ids=tag_ids)
    tags_by_sample = tag_resolver.get_tags_by_sample(session=session, tag_ids=tag_ids)
    return {
        sample_id: {names_by_id[tag_id] for tag_id in tags_by_sample.get(sample_id, set())}
        for sample_id in sample_ids
    }
