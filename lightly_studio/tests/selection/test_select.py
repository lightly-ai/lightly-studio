"""Test user selection functions."""

from __future__ import annotations

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.models.annotation.annotation_base import (
    AnnotationType,
)
from lightly_studio.resolvers import collection_resolver, image_resolver, tag_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.selection import select as select_file
from lightly_studio.selection.mundig import Mundig
from lightly_studio.selection.selection_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SelectionConfig,
)
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails, create_tag
from tests.selection import helpers_selection


class TestSelect:
    def test_diverse__embedding_model_name_unspecified(
        self, db_session: Session, mocker: MockerFixture
    ) -> None:
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            session=db_session, n_samples=20, embedding_model_names=["embedding_model_1"]
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None
        query = DatasetQuery(collection_table, db_session)
        spy_select_via_db = mocker.spy(select_file, "select_via_database")

        query.selection().diverse(
            n_samples_to_select=3, selection_result_tag_name="diverse_selection"
        )

        expected_sample_ids = [
            sample.sample_id for sample in DatasetQuery(collection_table, db_session)
        ]
        spy_select_via_db.assert_called_once_with(
            session=db_session,
            config=SelectionConfig(
                collection_id=collection_id,
                n_samples_to_select=3,
                selection_result_tag_name="diverse_selection",
                strategies=[EmbeddingDiversityStrategy(embedding_model_name=None)],
            ),
            input_sample_ids=expected_sample_ids,
        )

    def test_diverse__embedding_model_name_specified(
        self, db_session: Session, mocker: MockerFixture
    ) -> None:
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            session=db_session, n_samples=20, embedding_model_names=["embedding_model_1"]
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None
        query = DatasetQuery(collection_table, db_session)
        spy_select_via_db = mocker.spy(select_file, "select_via_database")

        query.selection().diverse(
            n_samples_to_select=3,
            selection_result_tag_name="diverse_selection",
            embedding_model_name="embedding_model_1",
        )

        expected_sample_ids = [
            sample.sample_id for sample in DatasetQuery(collection_table, db_session)
        ]
        spy_select_via_db.assert_called_once_with(
            session=db_session,
            config=SelectionConfig(
                collection_id=collection_id,
                n_samples_to_select=3,
                selection_result_tag_name="diverse_selection",
                strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
            ),
            input_sample_ids=expected_sample_ids,
        )

    def test_annotation_balancing(self, db_session: Session, mocker: MockerFixture) -> None:
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            session=db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None

        dummy_label = helpers_resolvers.create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="test-label"
        )

        all_samples = image_resolver.get_all_by_collection_id(
            session=db_session, pagination=None, collection_id=collection_id
        ).samples

        sample_id = all_samples[0].sample_id

        query = DatasetQuery(collection_table, db_session)

        helpers_resolvers.create_annotations(
            session=db_session,
            collection_id=collection_id,
            annotations=[
                AnnotationDetails(
                    sample_id=sample_id,
                    annotation_label_id=dummy_label.annotation_label_id,
                    annotation_type=AnnotationType.CLASSIFICATION,
                )
            ],
        )

        spy_select_via_db = mocker.spy(select_file, "select_via_database")

        query.selection().annotation_balancing(
            n_samples_to_select=5,
            selection_result_tag_name="balancing_selection",
            target_distribution="uniform",
        )

        expected_sample_ids = [sample.sample_id for sample in all_samples]

        spy_select_via_db.assert_called_once_with(
            session=db_session,
            config=SelectionConfig(
                collection_id=collection_id,
                n_samples_to_select=5,
                selection_result_tag_name="balancing_selection",
                strategies=[AnnotationClassBalancingStrategy(target_distribution="uniform")],
            ),
            input_sample_ids=expected_sample_ids,
        )

    def test_similarity(self, db_session: Session) -> None:
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            session=db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None
        query = DatasetQuery(collection_table, db_session)
        query_tag = create_tag(
            session=db_session, collection_id=collection_id, tag_name="query-tag"
        )
        all_samples = image_resolver.get_all_by_collection_id(
            session=db_session, pagination=None, collection_id=collection_id
        ).samples
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=query_tag.tag_id,
            sample_ids=[all_samples[0].sample_id, all_samples[1].sample_id],
        )

        query.selection().similarity(
            n_samples_to_select=2,
            selection_result_tag_name="similarity_selection",
            query_tag_name="query-tag",
            embedding_model_name="embedding_model_1",
        )

        tags = tag_resolver.get_all_by_collection_id(db_session, collection_id=collection_id)
        assert len(tags) == 2

        selection_tag = next(tag for tag in tags if tag.name == "similarity_selection")
        selected_samples = image_resolver.get_all_by_collection_id(
            session=db_session,
            collection_id=collection_id,
            pagination=None,
            filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[selection_tag.tag_id])),
        ).samples

        expected_sample_paths = {"sample_0.jpg", "sample_1.jpg"}
        actual_sample_paths = {sample.file_path_abs for sample in selected_samples}
        assert actual_sample_paths == expected_sample_paths

    def test_metadata_weighting(self, db_session: Session, mocker: MockerFixture) -> None:
        collection_id = helpers_selection.fill_db_with_samples_and_metadata(
            session=db_session, metadata=[16.0, 50.0, 35.0], metadata_key="speed"
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None
        query = DatasetQuery(collection_table, db_session)
        spy_select_via_db = mocker.spy(select_file, "select_via_database")
        spy_mundig_add_weighting = mocker.spy(Mundig, "add_weighting")

        query.selection().metadata_weighting(
            n_samples_to_select=2,
            metadata_key="speed",
            selection_result_tag_name="weight_selection",
        )

        expected_sample_ids = [
            sample.sample_id for sample in DatasetQuery(collection_table, db_session)
        ]
        spy_select_via_db.assert_called_once_with(
            session=db_session,
            config=SelectionConfig(
                collection_id=collection_id,
                n_samples_to_select=2,
                selection_result_tag_name="weight_selection",
                strategies=[MetadataWeightingStrategy(metadata_key="speed")],
            ),
            input_sample_ids=expected_sample_ids,
        )
        spy_mundig_add_weighting.assert_called_once_with(
            self=mocker.ANY, weights=[16.0, 50.0, 35.0], strength=1.0
        )

    def test_multi_strategies(self, db_session: Session, mocker: MockerFixture) -> None:
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            session=db_session, n_samples=5, embedding_model_names=["model_1", "model_2"]
        )
        helpers_selection.fill_db_metadata(
            session=db_session,
            collection_id=collection_id,
            metadata=[15.0, 47.0, 35.0, 18.0, 29.5],
            metadata_key="speed",
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None
        query = DatasetQuery(collection_table, db_session)
        spy_select_via_db = mocker.spy(select_file, "select_via_database")

        query.selection().multi_strategies(
            n_samples_to_select=3,
            selection_result_tag_name="multi_strategies_selection",
            selection_strategies=[
                EmbeddingDiversityStrategy(embedding_model_name="model_1"),
                EmbeddingDiversityStrategy(embedding_model_name="model_2"),
                MetadataWeightingStrategy(metadata_key="speed"),
            ],
        )

        expected_sample_ids = [
            sample.sample_id for sample in DatasetQuery(collection_table, db_session)
        ]
        spy_select_via_db.assert_called_once_with(
            session=db_session,
            config=SelectionConfig(
                collection_id=collection_id,
                n_samples_to_select=3,
                selection_result_tag_name="multi_strategies_selection",
                strategies=[
                    EmbeddingDiversityStrategy(embedding_model_name="model_1"),
                    EmbeddingDiversityStrategy(embedding_model_name="model_2"),
                    MetadataWeightingStrategy(metadata_key="speed"),
                ],
            ),
            input_sample_ids=expected_sample_ids,
        )
