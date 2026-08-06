from __future__ import annotations

from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images


class TestDatasetQueryRandomSplit:
    def test_random_split__no_filter_splits_whole_collection(self, db_session: Session) -> None:
        dataset = create_collection(session=db_session)
        create_images(
            db_session=db_session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path=f"s{i}.png") for i in range(10)],
        )

        query = DatasetQuery(dataset=dataset, session=db_session)
        result = query.random_split({"train": 80, "val": 10, "test": 10}, seed=42)

        assert result.counts == {"train": 8, "val": 1, "test": 1}
        assert result.seed == 42

    def test_random_split__with_filter_splits_only_matching(self, db_session: Session) -> None:
        dataset = create_collection(session=db_session)
        # Five wide images match the filter, five narrow ones do not.
        create_images(
            db_session=db_session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path=f"wide{i}.png", width=1920) for i in range(5)],
        )
        create_images(
            db_session=db_session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path=f"narrow{i}.png", width=10) for i in range(5)],
        )

        query = DatasetQuery(dataset=dataset, session=db_session)
        query.match(ImageSampleField.width > 100)
        result = query.random_split({"train": 60, "val": 40}, seed=1)

        assert result.counts == {"train": 3, "val": 2}
        assert sum(result.counts.values()) == 5

    def test_random_split__random_seed_is_returned(self, db_session: Session) -> None:
        dataset = create_collection(session=db_session)
        create_images(
            db_session=db_session,
            collection_id=dataset.collection_id,
            images=[ImageStub(path=f"s{i}.png") for i in range(4)],
        )

        query = DatasetQuery(dataset=dataset, session=db_session)
        result = query.random_split({"train": 50, "val": 50})

        # A seed was chosen and the split tags were created.
        assert isinstance(result.seed, int)
        train_tag = tag_resolver.get_by_name(
            session=db_session, tag_name="train", collection_id=dataset.collection_id
        )
        assert train_tag is not None
