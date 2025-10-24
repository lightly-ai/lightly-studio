from __future__ import annotations

from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from lightly_studio import Dataset, db_manager
from lightly_studio.api import features
from lightly_studio.core import dataset as dataset_module
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.core.dataset_query.sample_field import SampleField
from lightly_studio.dataset import embedding_manager
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import (
    SampleImage,
    create_dataset,
    create_embedding_model,
    create_sample,
    create_sample_embedding,
    create_samples,
)


class TestDataset:
    def test_create(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        assert dataset.name == "test_dataset"
        # Validate that the DatasetTable is created correctly
        assert dataset._inner.name == "test_dataset"
        samples = image_resolver.get_all_by_dataset_id(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
        ).samples
        assert len(samples) == 0

        # Test creating a second dataset with a default name
        dataset2 = Dataset.create()
        assert dataset2.name == "default_dataset"

    def test_create__duplicate_names(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        Dataset.create(name="test_dataset")

        with pytest.raises(ValueError, match="already exists"):
            Dataset.create(name="test_dataset")

    def test_load(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create two datasets
        dataset1 = Dataset.create(name="dataset1")
        Dataset.create(name="dataset2")

        # Load an existing dataset
        loaded_dataset1 = Dataset.load(name="dataset1")
        assert loaded_dataset1.name == "dataset1"
        assert loaded_dataset1.dataset_id == dataset1.dataset_id

        # Load non-existent dataset
        with pytest.raises(ValueError, match="Dataset with name 'non_existent' not found"):
            Dataset.load(name="non_existent")

    def test_load__default_name(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create two datasets, one with default name
        dataset1 = Dataset.create()
        Dataset.create(name="dataset2")

        # Load the dataset with the default name
        loaded_dataset1 = Dataset.load()
        assert loaded_dataset1.dataset_id == dataset1.dataset_id

    def test_load_or_create(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create a dataset
        dataset1 = Dataset.create(name="dataset1")

        # Load existing dataset
        loaded_dataset1 = Dataset.load_or_create(name="dataset1")
        assert loaded_dataset1.dataset_id == dataset1.dataset_id

        # Create new dataset
        new_dataset = Dataset.load_or_create(name="new_dataset")
        assert new_dataset.name == "new_dataset"
        assert new_dataset.dataset_id != dataset1.dataset_id

    def test_load_or_create__default_name(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create a dataset with default name
        dataset1 = Dataset.load_or_create()
        assert dataset1.name == "default_dataset"

        # Load existing dataset with default name
        loaded_dataset1 = Dataset.load_or_create()
        assert loaded_dataset1.dataset_id == dataset1.dataset_id

    def test_iterable(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create a dataset and add samples to it
        dataset = Dataset.create(name="test_dataset")
        images = [
            SampleImage(path="/path/to/image0.jpg", width=640, height=480),
            SampleImage(path="/path/to/image1.jpg", width=640, height=480),
            SampleImage(path="/path/to/image2.jpg", width=1024, height=768),
        ]
        create_samples(db_session=dataset.session, dataset_id=dataset.dataset_id, images=images)

        # Collect samples using the iterator interface
        collected_samples = list(iter(dataset))

        assert len(collected_samples) == 3
        assert collected_samples[0].file_path_abs == "/path/to/image0.jpg"
        assert collected_samples[0].height == 480
        assert collected_samples[0].width == 640
        assert collected_samples[1].file_path_abs == "/path/to/image1.jpg"
        assert collected_samples[1].height == 480
        assert collected_samples[1].width == 640
        assert collected_samples[2].file_path_abs == "/path/to/image2.jpg"
        assert collected_samples[2].height == 768
        assert collected_samples[2].width == 1024

    def test_get_sample(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create a dataset and add samples to it
        dataset = Dataset.create(name="test_dataset")

        sample1 = create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/image1.jpg",
            width=640,
            height=480,
        )
        sample2 = create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/image2.jpg",
            width=640,
            height=480,
        )

        out_sample1 = dataset.get_sample(sample_id=sample1.sample_id)
        assert out_sample1.sample_id == sample1.sample_id
        assert out_sample1.file_name == "image1.jpg"

        out_sample2 = dataset.get_sample(sample_id=sample2.sample_id)
        assert out_sample2.sample_id == sample2.sample_id
        assert out_sample2.file_name == "image2.jpg"

    def test_update_sample(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create a dataset and add samples to it
        dataset = Dataset.create(name="test_dataset")

        sample = create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/image1.jpg",
            width=640,
            height=480,
        )
        sample_to_update = dataset.get_sample(sample_id=sample.sample_id)
        # add a tag so that the sample ID is used as foreign key somewhere
        sample_to_update.add_tag("tag1")
        sample_to_update.file_path_abs = "/new/path/to/image1_renamed.jpg"
        assert sample_to_update.file_path_abs == "/new/path/to/image1_renamed.jpg"

    def test_get_sample__empty(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create a dataset and one sample
        dataset = Dataset.create(name="test_dataset")
        sample_id_mod = UUID(int=123)

        # Assert that an error is raised when trying to get a non-existent sample by file_path
        with pytest.raises(IndexError, match=f"No sample found for sample_id: {sample_id_mod}"):
            _ = dataset.get_sample(sample_id=sample_id_mod)

    def test_query(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        sample1 = create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/image1.jpg",
        )
        create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/image2.jpg",
        )
        samples = dataset.query().match(SampleField.file_name == "image1.jpg").to_list()
        assert len(samples) == 1
        assert samples[0].sample_id == sample1.sample_id

    def test_match(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        sample1 = create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/image1.jpg",
        )
        create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/image2.jpg",
        )
        samples = dataset.match(SampleField.file_name == "image1.jpg").to_list()
        assert len(samples) == 1
        assert samples[0].sample_id == sample1.sample_id

    def test_slice(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/zebra.jpg",
        )
        create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/alpha.jpg",
        )
        create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/beta.jpg",
        )

        result_samples = dataset.slice(offset=0, limit=2).to_list()
        assert len(result_samples) == 2
        # Should be the first two samples: zebra.jpg, alpha.jpg
        assert result_samples[0].file_name == "zebra.jpg"
        assert result_samples[1].file_name == "alpha.jpg"

        # Try the same test but using [1:3] instead of .slice()
        result_samples = dataset[1:3].to_list()
        assert len(result_samples) == 2
        # Should be the last two samples: alpha.jpg, beta.jpg
        assert result_samples[0].file_name == "alpha.jpg"
        assert result_samples[1].file_name == "beta.jpg"

    def test_order_by(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/zebra.jpg",
        )
        create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/alpha.jpg",
        )
        create_sample(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            file_path_abs="/path/to/beta.jpg",
        )
        result_samples = dataset.order_by(OrderByField(SampleField.file_name).desc()).to_list()

        assert len(result_samples) == 3
        # Should be ordered reverse alphabetically: zebra.jpg, beta.jpg, alpha.jpg
        assert result_samples[0].file_name == "zebra.jpg"
        assert result_samples[1].file_name == "beta.jpg"
        assert result_samples[2].file_name == "alpha.jpg"

    def test_compute_typicality_metadata(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        embedding_model = create_embedding_model(
            session=dataset.session,
            dataset_id=dataset.dataset_id,
            embedding_model_name="example_embedding_model",
        )
        embedding_model_id = embedding_model.embedding_model_id
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
        ]
        for i, embedding in enumerate(embeddings):
            sample = create_sample(
                session=dataset.session,
                dataset_id=dataset.dataset_id,
                file_path_abs=f"sample{i}.jpg",
            )
            create_sample_embedding(
                session=dataset.session,
                sample_id=sample.sample_id,
                embedding=embedding,
                embedding_model_id=embedding_model_id,
            )

        dataset.compute_typicality_metadata()
        samples = list(dataset.query())
        assert samples[0].metadata["typicality"] == pytest.approx(0.3225063)
        assert samples[1].metadata["typicality"] == pytest.approx(0.4222289)
        assert samples[2].metadata["typicality"] == pytest.approx(0.3853082)


def test_generate_embeddings(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    dataset = create_dataset(session=session)
    sample1 = create_sample(session=session, dataset_id=dataset.dataset_id)

    assert len(sample1.sample.embeddings) == 0
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features

    dataset_module._generate_embeddings(
        session=session,
        dataset_id=dataset.dataset_id,
        sample_ids=[sample1.sample_id],
    )
    assert len(sample1.sample.embeddings) == 1
    assert "embeddingSearchEnabled" in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" in features.lightly_studio_active_features


def test_generate_embeddings__no_generator(
    mocker: MockerFixture,
    patch_dataset: None,  # noqa: ARG001
) -> None:
    mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=None,
    )

    session = db_manager.persistent_session()
    dataset = create_dataset(session=session)
    sample1 = create_sample(session=session, dataset_id=dataset.dataset_id)
    assert len(sample1.sample.embeddings) == 0
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features

    dataset_module._generate_embeddings(
        session=session,
        dataset_id=dataset.dataset_id,
        sample_ids=[sample1.sample_id],
    )
    assert len(sample1.sample.embeddings) == 0
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features


def test_generate_embeddings__empty_sample_ids(
    mocker: MockerFixture,
    patch_dataset: None,  # noqa: ARG001
) -> None:
    spy_load_model = mocker.spy(embedding_manager, "_load_embedding_generator_from_env")

    session = db_manager.persistent_session()
    dataset = create_dataset(session=session)

    dataset_module._generate_embeddings(
        session=session,
        dataset_id=dataset.dataset_id,
        sample_ids=[],
    )

    # Model loading should be skipped when sample_ids is empty
    spy_load_model.assert_not_called()
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features


def test_are_embeddings_available(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    dataset = create_dataset(session=session)
    sample1 = create_sample(session=session, dataset_id=dataset.dataset_id)

    assert (
        dataset_module._are_embeddings_available(
            session=session,
            dataset_id=dataset.dataset_id,
        )
        is False
    )

    dataset_module._generate_embeddings(
        session=session,
        dataset_id=dataset.dataset_id,
        sample_ids=[sample1.sample_id],
    )
    assert (
        dataset_module._are_embeddings_available(
            session=session,
            dataset_id=dataset.dataset_id,
        )
        is True
    )


def test_enable_few_shot_classifier_on_load(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    dataset = create_dataset(session=session, dataset_name="test_dataset")
    sample1 = create_sample(session=session, dataset_id=dataset.dataset_id)

    assert len(sample1.sample.embeddings) == 0
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features

    dataset_module._generate_embeddings(
        session=session,
        dataset_id=dataset.dataset_id,
        sample_ids=[sample1.sample_id],
    )
    assert len(sample1.sample.embeddings) == 1
    assert "embeddingSearchEnabled" in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" in features.lightly_studio_active_features

    features.lightly_studio_active_features.clear()
    # Load an existing dataset should enable the features as we have embeddings.
    Dataset.load(name="test_dataset")
    assert "embeddingSearchEnabled" in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" in features.lightly_studio_active_features


def test_enable_few_shot_classifier_on_load__no_embeddings(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    dataset = create_dataset(session=session, dataset_name="test_dataset")
    create_sample(session=session, dataset_id=dataset.dataset_id)

    # Load an existing dataset without embeddings. Should not enable the features.
    Dataset.load(name="test_dataset")
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features


def test_enable_few_shot_classifier_on_load_or_create(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    dataset = create_dataset(session=session, dataset_name="test_dataset")
    sample1 = create_sample(session=session, dataset_id=dataset.dataset_id)
    dataset_module._generate_embeddings(
        session=session,
        dataset_id=dataset.dataset_id,
        sample_ids=[sample1.sample_id],
    )
    assert len(sample1.sample.embeddings) == 1
    assert "embeddingSearchEnabled" in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" in features.lightly_studio_active_features

    features.lightly_studio_active_features.clear()
    # Load an existing dataset should enable the features.
    Dataset.load_or_create(name="test_dataset")
    assert "embeddingSearchEnabled" in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" in features.lightly_studio_active_features

    features.lightly_studio_active_features.clear()
    # Creating a new dataset should not enable the features.
    Dataset.load_or_create(name="non_existing_dataset_name")
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features
