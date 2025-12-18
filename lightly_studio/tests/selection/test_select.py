"""Test user selection functions."""

from __future__ import annotations

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.models.annotation.annotation_base import (
    AnnotationType,
)
from lightly_studio.resolvers import collection_resolver, image_resolver
from lightly_studio.selection import select as select_file
from lightly_studio.selection.mundig import Mundig
from lightly_studio.selection.selection_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SelectionConfig,
)
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails
from tests.selection import helpers_selection


class TestSelect:
    def test_diverse__embedding_model_name_unspecified(
        self, test_db: Session, mocker: MockerFixture
    ) -> None:
        dataset_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            test_db=test_db, n_samples=20, embedding_model_names=["embedding_model_1"]
        )
        dataset_table = collection_resolver.get_by_id(test_db, dataset_id)
        assert dataset_table is not None
        query = DatasetQuery(dataset_table, test_db)
        spy_select_via_db = mocker.spy(select_file, "select_via_database")

        query.selection().diverse(
            n_samples_to_select=3, selection_result_tag_name="diverse_selection"
        )

        expected_sample_ids = [sample.sample_id for sample in DatasetQuery(dataset_table, test_db)]
        spy_select_via_db.assert_called_once_with(
            session=test_db,
            config=SelectionConfig(
                collection_id=dataset_id,
                n_samples_to_select=3,
                selection_result_tag_name="diverse_selection",
                strategies=[EmbeddingDiversityStrategy(embedding_model_name=None)],
            ),
            input_sample_ids=expected_sample_ids,
        )

    def test_diverse__embedding_model_name_specified(
        self, test_db: Session, mocker: MockerFixture
    ) -> None:
        dataset_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            test_db=test_db, n_samples=20, embedding_model_names=["embedding_model_1"]
        )
        dataset_table = collection_resolver.get_by_id(test_db, dataset_id)
        assert dataset_table is not None
        query = DatasetQuery(dataset_table, test_db)
        spy_select_via_db = mocker.spy(select_file, "select_via_database")

        query.selection().diverse(
            n_samples_to_select=3,
            selection_result_tag_name="diverse_selection",
            embedding_model_name="embedding_model_1",
        )

        expected_sample_ids = [sample.sample_id for sample in DatasetQuery(dataset_table, test_db)]
        spy_select_via_db.assert_called_once_with(
            session=test_db,
            config=SelectionConfig(
                collection_id=dataset_id,
                n_samples_to_select=3,
                selection_result_tag_name="diverse_selection",
                strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
            ),
            input_sample_ids=expected_sample_ids,
        )

    def test_annotation_balancing(self, test_db: Session, mocker: MockerFixture) -> None:
        dataset_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            test_db=test_db, n_samples=5, embedding_model_names=["embedding_model_1"]
        )
        dataset_table = collection_resolver.get_by_id(test_db, dataset_id)
        assert dataset_table is not None

        dummy_label = helpers_resolvers.create_annotation_label(
            session=test_db, annotation_label_name="test-label"
        )

        all_samples = image_resolver.get_all_by_collection_id(
            session=test_db, pagination=None, collection_id=dataset_id
        ).samples

        sample_id = all_samples[0].sample_id

        query = DatasetQuery(dataset_table, test_db)

        helpers_resolvers.create_annotations(
            session=test_db,
            collection_id=dataset_id,
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
            session=test_db,
            config=SelectionConfig(
                collection_id=dataset_id,
                n_samples_to_select=5,
                selection_result_tag_name="balancing_selection",
                strategies=[AnnotationClassBalancingStrategy(target_distribution="uniform")],
            ),
            input_sample_ids=expected_sample_ids,
        )

    def test_metadata_weighting(self, test_db: Session, mocker: MockerFixture) -> None:
        dataset_id = helpers_selection.fill_db_with_samples_and_metadata(
            test_db=test_db, metadata=[16.0, 50.0, 35.0], metadata_key="speed"
        )
        dataset_table = collection_resolver.get_by_id(test_db, dataset_id)
        assert dataset_table is not None
        query = DatasetQuery(dataset_table, test_db)
        spy_select_via_db = mocker.spy(select_file, "select_via_database")
        spy_mundig_add_weighting = mocker.spy(Mundig, "add_weighting")

        query.selection().metadata_weighting(
            n_samples_to_select=2,
            metadata_key="speed",
            selection_result_tag_name="weight_selection",
        )

        expected_sample_ids = [sample.sample_id for sample in DatasetQuery(dataset_table, test_db)]
        spy_select_via_db.assert_called_once_with(
            session=test_db,
            config=SelectionConfig(
                collection_id=dataset_id,
                n_samples_to_select=2,
                selection_result_tag_name="weight_selection",
                strategies=[MetadataWeightingStrategy(metadata_key="speed")],
            ),
            input_sample_ids=expected_sample_ids,
        )
        spy_mundig_add_weighting.assert_called_once_with(
            self=mocker.ANY, weights=[16.0, 50.0, 35.0], strength=1.0
        )

    def test_multi_strategies(self, test_db: Session, mocker: MockerFixture) -> None:
        dataset_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            test_db=test_db, n_samples=5, embedding_model_names=["model_1", "model_2"]
        )
        helpers_selection.fill_db_metadata(
            test_db=test_db,
            collection_id=dataset_id,
            metadata=[15.0, 47.0, 35.0, 18.0, 29.5],
            metadata_key="speed",
        )
        dataset_table = collection_resolver.get_by_id(test_db, dataset_id)
        assert dataset_table is not None
        query = DatasetQuery(dataset_table, test_db)
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

        expected_sample_ids = [sample.sample_id for sample in DatasetQuery(dataset_table, test_db)]
        spy_select_via_db.assert_called_once_with(
            session=test_db,
            config=SelectionConfig(
                collection_id=dataset_id,
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
