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
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import image_resolver, tag_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
    create_samples_with_embeddings,
    create_tag,
)


class TestDataset:
    def test_create(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        assert dataset.name == "test_dataset"
        # Validate that the CollectionTable is created correctly
        assert dataset._inner.name == "test_dataset"
        samples = image_resolver.get_all_by_collection_id(
            session=dataset.session,
            collection_id=dataset.dataset_id,
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

    def test_create__sample_type(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset", sample_type=SampleType.VIDEO)
        assert dataset._inner.sample_type == SampleType.VIDEO

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

    def test_load_or_create__sample_type(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.load_or_create(sample_type=SampleType.VIDEO)
        assert dataset._inner.sample_type == SampleType.VIDEO

    def test_load_or_create__sample_type_mismatch(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        Dataset.create(sample_type=SampleType.IMAGE)
        with pytest.raises(
            ValueError, match="already exists with sample type 'image', but 'video' was requested"
        ):
            Dataset.load_or_create(sample_type=SampleType.VIDEO)

    def test_iterable(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create a dataset and add samples to it
        dataset = Dataset.create(name="test_dataset")
        images = [
            ImageStub(path="/path/to/image0.jpg", width=640, height=480),
            ImageStub(path="/path/to/image1.jpg", width=640, height=480),
            ImageStub(path="/path/to/image2.jpg", width=1024, height=768),
        ]
        create_images(db_session=dataset.session, collection_id=dataset.dataset_id, images=images)

        # Collect samples using the iterator interface
        collected_samples = sorted(iter(dataset), key=lambda sample: sample.file_path_abs)

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

        image1 = create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/image1.jpg",
            width=640,
            height=480,
        )
        image2 = create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/image2.jpg",
            width=640,
            height=480,
        )

        out_sample1 = dataset.get_sample(sample_id=image1.sample_id)
        assert out_sample1.sample_id == image1.sample_id
        assert out_sample1.file_name == "image1.jpg"

        out_sample2 = dataset.get_sample(sample_id=image2.sample_id)
        assert out_sample2.sample_id == image2.sample_id
        assert out_sample2.file_name == "image2.jpg"

    def test_update_sample(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        # Create a dataset and add samples to it
        dataset = Dataset.create(name="test_dataset")

        image = create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/image1.jpg",
            width=640,
            height=480,
        )
        sample_to_update = dataset.get_sample(sample_id=image.sample_id)
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
        image1 = create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/image1.jpg",
        )
        create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/image2.jpg",
        )
        samples = dataset.query().match(SampleField.file_name == "image1.jpg").to_list()
        assert len(samples) == 1
        assert samples[0].sample_id == image1.sample_id

    def test_match(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        image1 = create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/image1.jpg",
        )
        create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/image2.jpg",
        )
        samples = dataset.match(SampleField.file_name == "image1.jpg").to_list()
        assert len(samples) == 1
        assert samples[0].sample_id == image1.sample_id

    def test_slice(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/zebra.jpg",
        )
        create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/alpha.jpg",
        )
        create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
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
        create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/zebra.jpg",
        )
        create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            file_path_abs="/path/to/alpha.jpg",
        )
        create_image(
            session=dataset.session,
            collection_id=dataset.dataset_id,
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
            collection_id=dataset.dataset_id,
            embedding_model_name="example_embedding_model",
        )
        create_samples_with_embeddings(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            embedding_model_id=embedding_model.embedding_model_id,
            images_and_embeddings=[
                (ImageStub(path="sample0.jpg"), [1.0, 0.0, 0.0]),
                (ImageStub(path="sample1.jpg"), [0.0, 1.0, 0.0]),
                (ImageStub(path="sample2.jpg"), [0.0, 1.0, 1.0]),
            ],
        )

        dataset.compute_typicality_metadata()
        samples = list(dataset.query())
        assert samples[0].metadata["typicality"] == pytest.approx(0.3225063)
        assert samples[1].metadata["typicality"] == pytest.approx(0.4222289)
        assert samples[2].metadata["typicality"] == pytest.approx(0.3853082)

    def test_compute_similarity_metadata(
        self,
        patch_dataset: None,  # noqa: ARG002
    ) -> None:
        dataset = Dataset.create(name="test_dataset")
        embedding_model = create_embedding_model(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            embedding_model_name="example_embedding_model",
        )
        create_samples_with_embeddings(
            session=dataset.session,
            collection_id=dataset.dataset_id,
            embedding_model_id=embedding_model.embedding_model_id,
            images_and_embeddings=[
                (ImageStub(path="img0.jpg"), [1.0, 0.0, 0.0]),
                (ImageStub(path="img1.jpg"), [0.9, 0.0, 0.0]),
                (ImageStub(path="img2.jpg"), [0.0, 1.0, 0.0]),
                (ImageStub(path="img3.jpg"), [0.0, 0.0, 1.0]),
            ],
        )

        samples = list(dataset.query())
        query_tag = create_tag(
            session=dataset.session, collection_id=dataset.dataset_id, tag_name="query"
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=dataset.session,
            tag_id=query_tag.tag_id,
            sample_ids=[samples[0].sample_id, samples[2].sample_id],
        )

        metadata_name = dataset.compute_similarity_metadata(query_tag_name="query")
        assert metadata_name.startswith("similarity_query_20")

        enriched_samples = list(dataset.query())
        # The nearest neighbor of embedding1 is embedding0 with distance 0.1.
        # The nearest neighbor of embedding3 is embedding2 with distance sqrt(2).
        # Distance to the nearest neighbor is converted to similarity score, which is inversely
        # proportional to distance. Similarity of sample1 is therefore higher than similarity of
        # sample3.
        assert enriched_samples[1].metadata[metadata_name] == pytest.approx(0.7678481)
        assert enriched_samples[3].metadata[metadata_name] == pytest.approx(0.023853203)

        # The query samples have the maximum similarity value of 1.0.
        assert enriched_samples[0].metadata[metadata_name] == 1.0
        assert enriched_samples[2].metadata[metadata_name] == 1.0


def test_generate_embeddings(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    dataset = create_collection(session=session)
    image1 = create_image(session=session, collection_id=dataset.collection_id)

    assert len(image1.sample.embeddings) == 0
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features

    dataset_module._generate_embeddings_image(
        session=session,
        collection_id=dataset.collection_id,
        sample_ids=[image1.sample_id],
    )
    assert len(image1.sample.embeddings) == 1
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
    dataset = create_collection(session=session)
    image1 = create_image(session=session, collection_id=dataset.collection_id)
    assert len(image1.sample.embeddings) == 0
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features

    dataset_module._generate_embeddings_image(
        session=session,
        collection_id=dataset.collection_id,
        sample_ids=[image1.sample_id],
    )
    assert len(image1.sample.embeddings) == 0
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features


def test_generate_embeddings__empty_sample_ids(
    mocker: MockerFixture,
    patch_dataset: None,  # noqa: ARG001
) -> None:
    spy_load_model = mocker.spy(embedding_manager, "_load_embedding_generator_from_env")

    session = db_manager.persistent_session()
    dataset = create_collection(session=session)

    dataset_module._generate_embeddings_image(
        session=session,
        collection_id=dataset.collection_id,
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
    dataset = create_collection(session=session)
    image1 = create_image(session=session, collection_id=dataset.collection_id)

    assert (
        dataset_module._are_embeddings_available(
            session=session,
            collection_id=dataset.collection_id,
        )
        is False
    )

    dataset_module._generate_embeddings_image(
        session=session,
        collection_id=dataset.collection_id,
        sample_ids=[image1.sample_id],
    )
    assert (
        dataset_module._are_embeddings_available(
            session=session,
            collection_id=dataset.collection_id,
        )
        is True
    )


def test_enable_few_shot_classifier_on_load(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    dataset = create_collection(session=session, collection_name="test_dataset")
    image1 = create_image(session=session, collection_id=dataset.collection_id)

    assert len(image1.sample.embeddings) == 0
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features

    dataset_module._generate_embeddings_image(
        session=session,
        collection_id=dataset.collection_id,
        sample_ids=[image1.sample_id],
    )
    assert len(image1.sample.embeddings) == 1
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
    dataset = create_collection(session=session, collection_name="test_dataset")
    create_image(session=session, collection_id=dataset.collection_id)

    # Load an existing dataset without embeddings. Should not enable the features.
    Dataset.load(name="test_dataset")
    assert "embeddingSearchEnabled" not in features.lightly_studio_active_features
    assert "fewShotClassifierEnabled" not in features.lightly_studio_active_features


def test_enable_few_shot_classifier_on_load_or_create(
    patch_dataset: None,  # noqa: ARG001
) -> None:
    session = db_manager.persistent_session()
    dataset = create_collection(session=session, collection_name="test_dataset")
    image1 = create_image(session=session, collection_id=dataset.collection_id)
    dataset_module._generate_embeddings_image(
        session=session,
        collection_id=dataset.collection_id,
        sample_ids=[image1.sample_id],
    )
    assert len(image1.sample.embeddings) == 1
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
