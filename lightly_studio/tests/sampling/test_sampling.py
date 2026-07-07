"""Test user sampling functions."""

from __future__ import annotations

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.models.annotation.annotation_base import (
    AnnotationType,
)
from lightly_studio.resolvers import collection_resolver, image_resolver
from lightly_studio.sampling import sample as sampling_file
from lightly_studio.sampling.mundig import Mundig
from lightly_studio.sampling.sampling_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SamplingConfig,
)
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames
from tests.sampling import helpers_sampling


class TestSampling:
    def test_diverse__embedding_model_name_unspecified(
        self, db_session: Session, mocker: MockerFixture
    ) -> None:
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            session=db_session, n_samples=20, embedding_model_names=["embedding_model_1"]
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None
        query = DatasetQuery(collection_table, db_session)
        spy_sampling_via_db = mocker.spy(sampling_file, "sampling_via_database")

        query.sampling().diverse(n_samples_to_select=3, sampling_result_tag_name="diverse_sampling")

        expected_sample_ids = [
            sample.sample_id for sample in DatasetQuery(collection_table, db_session)
        ]
        spy_sampling_via_db.assert_called_once_with(
            session=db_session,
            config=SamplingConfig(
                collection_id=collection_id,
                n_samples_to_select=3,
                sampling_result_tag_name="diverse_sampling",
                strategies=[EmbeddingDiversityStrategy(embedding_model_name=None)],
            ),
            input_sample_ids=expected_sample_ids,
        )

    def test_diverse__embedding_model_name_unspecified__video_frames(
        self,
        patch_collection: None,  # noqa: ARG002
        mocker: MockerFixture,
    ) -> None:
        dataset = VideoDataset.create(name="video_dataset")
        create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="/data/a.mp4", duration_s=1.0, fps=3.0),
        )
        create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="/data/b.mp4", duration_s=1.0, fps=2.0),
        )
        frames = dataset.frames()
        embedding_model = helpers_resolvers.create_embedding_model(
            session=dataset.session,
            collection_id=frames.collection_id,
            embedding_model_name="embedding_model_1",
        )
        for i, frame in enumerate(frames):
            helpers_resolvers.create_sample_embedding(
                session=dataset.session,
                sample_id=frame.sample_id,
                embedding_model_id=embedding_model.embedding_model_id,
                embedding=[i, i],
            )

        spy_sampling_via_db = mocker.spy(sampling_file, "sampling_via_database")

        frames.query().sampling().diverse(
            n_samples_to_select=2,
            sampling_result_tag_name="diverse_frames",
        )

        expected_sample_ids = [frame.sample_id for frame in frames]
        spy_sampling_via_db.assert_called_once_with(
            session=dataset.session,
            config=SamplingConfig(
                collection_id=frames.collection_id,
                n_samples_to_select=2,
                sampling_result_tag_name="diverse_frames",
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
        spy_sampling_via_db = mocker.spy(sampling_file, "sampling_via_database")

        query.sampling().diverse(
            n_samples_to_select=3,
            sampling_result_tag_name="diverse_sampling",
            embedding_model_name="embedding_model_1",
        )

        expected_sample_ids = [
            sample.sample_id for sample in DatasetQuery(collection_table, db_session)
        ]
        spy_sampling_via_db.assert_called_once_with(
            session=db_session,
            config=SamplingConfig(
                collection_id=collection_id,
                n_samples_to_select=3,
                sampling_result_tag_name="diverse_sampling",
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

        spy_sampling_via_db = mocker.spy(sampling_file, "sampling_via_database")

        query.sampling().annotation_balancing(
            n_samples_to_select=5,
            sampling_result_tag_name="balancing_sampling",
            target_distribution="uniform",
        )

        expected_sample_ids = [sample.sample_id for sample in all_samples]

        spy_sampling_via_db.assert_called_once_with(
            session=db_session,
            config=SamplingConfig(
                collection_id=collection_id,
                n_samples_to_select=5,
                sampling_result_tag_name="balancing_sampling",
                strategies=[AnnotationClassBalancingStrategy(target_distribution="uniform")],
            ),
            input_sample_ids=expected_sample_ids,
        )

    def test_metadata_weighting(self, db_session: Session, mocker: MockerFixture) -> None:
        collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
            session=db_session, metadata=[16.0, 50.0, 35.0], metadata_key="speed"
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None
        query = DatasetQuery(collection_table, db_session)
        spy_sampling_via_db = mocker.spy(sampling_file, "sampling_via_database")
        spy_mundig_add_weighting = mocker.spy(Mundig, "add_weighting")

        query.sampling().metadata_weighting(
            n_samples_to_select=2,
            metadata_key="speed",
            sampling_result_tag_name="weight_sampling",
        )

        expected_sample_ids = [
            sample.sample_id for sample in DatasetQuery(collection_table, db_session)
        ]
        spy_sampling_via_db.assert_called_once_with(
            session=db_session,
            config=SamplingConfig(
                collection_id=collection_id,
                n_samples_to_select=2,
                sampling_result_tag_name="weight_sampling",
                strategies=[MetadataWeightingStrategy(metadata_key="speed")],
            ),
            input_sample_ids=expected_sample_ids,
        )
        spy_mundig_add_weighting.assert_called_once_with(
            self=mocker.ANY, weights=[16.0, 50.0, 35.0], strength=1.0
        )

    def test_metadata_weighting__video_frames(
        self,
        patch_collection: None,  # noqa: ARG002
        mocker: MockerFixture,
    ) -> None:
        dataset = VideoDataset.create(name="video_dataset")
        create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="/data/a.mp4", duration_s=1.0, fps=3.0),
        )
        create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="/data/b.mp4", duration_s=1.0, fps=2.0),
        )
        frames = dataset.frames()
        query = frames.query()
        for frame in frames:
            frame.metadata["score"] = float(frame.frame_number)

        spy_sampling_via_db = mocker.spy(sampling_file, "sampling_via_database")
        spy_mundig_add_weighting = mocker.spy(Mundig, "add_weighting")

        query.sampling().metadata_weighting(
            n_samples_to_select=2,
            metadata_key="score",
            sampling_result_tag_name="weighted_frames",
        )

        expected_sample_ids = [frame.sample_id for frame in frames]
        spy_sampling_via_db.assert_called_once_with(
            session=dataset.session,
            config=SamplingConfig(
                collection_id=frames.collection_id,
                n_samples_to_select=2,
                sampling_result_tag_name="weighted_frames",
                strategies=[MetadataWeightingStrategy(metadata_key="score")],
            ),
            input_sample_ids=expected_sample_ids,
        )
        spy_mundig_add_weighting.assert_called_once_with(
            self=mocker.ANY, weights=[0.0, 1.0, 2.0, 0.0, 1.0], strength=1.0
        )

    def test_multi_strategies(self, db_session: Session, mocker: MockerFixture) -> None:
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            session=db_session, n_samples=5, embedding_model_names=["model_1", "model_2"]
        )
        helpers_sampling.fill_db_metadata(
            session=db_session,
            collection_id=collection_id,
            metadata=[15.0, 47.0, 35.0, 18.0, 29.5],
            metadata_key="speed",
        )
        collection_table = collection_resolver.get_by_id(db_session, collection_id)
        assert collection_table is not None
        query = DatasetQuery(collection_table, db_session)
        spy_sampling_via_db = mocker.spy(sampling_file, "sampling_via_database")

        query.sampling().multi_strategies(
            n_samples_to_select=3,
            sampling_result_tag_name="multi_strategies_sampling",
            sampling_strategies=[
                EmbeddingDiversityStrategy(embedding_model_name="model_1"),
                EmbeddingDiversityStrategy(embedding_model_name="model_2"),
                MetadataWeightingStrategy(metadata_key="speed"),
            ],
        )

        expected_sample_ids = [
            sample.sample_id for sample in DatasetQuery(collection_table, db_session)
        ]
        spy_sampling_via_db.assert_called_once_with(
            session=db_session,
            config=SamplingConfig(
                collection_id=collection_id,
                n_samples_to_select=3,
                sampling_result_tag_name="multi_strategies_sampling",
                strategies=[
                    EmbeddingDiversityStrategy(embedding_model_name="model_1"),
                    EmbeddingDiversityStrategy(embedding_model_name="model_2"),
                    MetadataWeightingStrategy(metadata_key="speed"),
                ],
            ),
            input_sample_ids=expected_sample_ids,
        )
