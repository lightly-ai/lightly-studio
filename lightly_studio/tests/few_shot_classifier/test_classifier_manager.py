from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio import few_shot_classifier
from lightly_studio.few_shot_classifier.classifier import AnnotatedEmbedding
from lightly_studio.few_shot_classifier.classifier_manager import (
    HIGH_CONFIDENCE_SAMPLES_NEEDED,
    LOW_CONFIDENCE_SAMPLES_NEEDED,
    ClassifierEntry,
    ClassifierManager,
)
from lightly_studio.few_shot_classifier.random_forest_classifier import (
    RandomForest,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.embedding_model import (
    EmbeddingModelTable,
)
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample_embedding import (
    SampleEmbeddingCreate,
    SampleEmbeddingTable,
)
from lightly_studio.resolvers import (
    annotation_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)


class TestClassifierManager:
    """Test the Classifier Manager."""

    def test_create_classifier(
        self,
        db_session: Session,
        mocker: MockerFixture,
    ) -> None:
        """Test creating a new classifier."""
        classifier_manager = ClassifierManager()
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable()],
        )
        # Create input data with two classes.
        input_classes = ["class1", "class2"]
        # Create classifier
        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=input_classes,
            dataset_id=uuid4(),
        )
        assert not classifier.is_active

    def test_commit_temp_classifier(
        self,
        db_session: Session,
        mocker: MockerFixture,
    ) -> None:
        """Test creating a new classifier."""
        classifier_manager = ClassifierManager()
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable(embedding_model_hash=str(uuid4()))],
        )
        mocker.patch.object(
            embedding_model_resolver,
            "get_by_model_hash",
            return_value=EmbeddingModelTable(),
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[
                AnnotatedEmbedding(embedding=[0.1, 0.2, 0.3], annotation="class1"),
                AnnotatedEmbedding(embedding=[0.4, 0.5, 0.6], annotation="class1"),
                AnnotatedEmbedding(embedding=[0.7, 0.8, 0.9], annotation="class2"),
            ],
        )
        # Create input data with two classes.
        input_clases = ["class1", "class2"]
        # Create classifier.
        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=input_clases,
            dataset_id=uuid4(),
        )
        assert not classifier.is_active
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations={
                "class1": [uuid4(), uuid4()],
                "class2": [uuid4()],
            },
        )
        classifier_manager.train_classifier(
            session=db_session, classifier_id=classifier.classifier_id
        )
        classifier_manager.commit_temp_classifier(classifier.classifier_id)
        assert classifier.is_active

    def test_commit_temp_classifier__classifier_not_found(self) -> None:
        classifier_manager = ClassifierManager()
        with pytest.raises(ValueError, match="Classifier with ID .* not found"):
            classifier_manager.commit_temp_classifier(classifier_id=uuid4())

    def test_train(
        self,
        db_session: Session,
        mocker: MockerFixture,
    ) -> None:
        """Test creating a new classifier."""
        classifier_manager = ClassifierManager()
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable(embedding_model_hash=str(uuid4()))],
        )
        mocker.patch.object(
            embedding_model_resolver,
            "get_by_model_hash",
            return_value=EmbeddingModelTable(),
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[AnnotatedEmbedding(embedding=[0.1, 0.2, 0.3], annotation="class1")],
        )
        # Create input data with two classes.
        input_clases = ["class1"]
        # Create classifier.
        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=input_clases,
            dataset_id=uuid4(),
        )

        assert not classifier.is_active
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations={
                "class1": [uuid4(), uuid4()],
            },
        )
        classifier_manager.train_classifier(
            session=db_session, classifier_id=classifier.classifier_id
        )
        assert classifier.few_shot_classifier.is_trained()

    def test_drop_classifier(
        self,
        db_session: Session,
        mocker: MockerFixture,
    ) -> None:
        """Test dropping a classifier in the finetuning step."""
        classifier_manager = ClassifierManager()
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable()],
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[
                AnnotatedEmbedding(embedding=[0.1, 0.2, 0.3], annotation="class1"),
                AnnotatedEmbedding(embedding=[0.4, 0.5, 0.6], annotation="class1"),
                AnnotatedEmbedding(embedding=[0.7, 0.8, 0.9], annotation="class2"),
            ],
        )
        # Create input data with two classes
        input_classes = ["class1", "class2"]
        # Create classifier
        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=input_classes,
            dataset_id=uuid4(),
        )
        classifier_manager.drop_temp_classifier(classifier.classifier_id)
        assert classifier.classifier_id not in classifier_manager._classifiers

    def test_drop_classifier__invalid_classifier_id(self) -> None:
        """Test dropping a classifier with a wrong id."""
        classifier_manager = ClassifierManager()
        classifier_id = uuid4()
        with pytest.raises(ValueError, match=f"Classifier with ID {classifier_id} not found."):
            classifier_manager.drop_temp_classifier(classifier_id)

    def test_provide_negative_samples(
        self,
        db_session: Session,
        samples: list[ImageTable],
        mocker: MockerFixture,
    ) -> None:
        """Test providing negative samples."""
        classifier_manager = ClassifierManager()
        # Mock the sample resolver to return a list of samples
        mocker.patch.object(
            image_resolver,
            "get_samples_excluding",
            return_value=samples,
        )
        # Get negative samples
        negative_samples = classifier_manager.provide_negative_samples(
            session=db_session,
            dataset_id=uuid4(),
            selected_samples=[],
            limit=10,
        )

        assert len(negative_samples) == 10

    def test_save_and_load_classifier(
        self,
        db_session: Session,
        tmp_path: Path,
        classifier: ClassifierEntry,
        classifier_manager: ClassifierManager,
    ) -> None:
        """Test saving a classifier to file and loading it back."""
        save_path = tmp_path / "classifier.pkl"
        classifier_manager.save_classifier_to_file(
            classifier_id=classifier.classifier_id, file_path=save_path
        )

        # Load classifier and verify
        loaded_classifier = classifier_manager.load_classifier_from_file(
            session=db_session,
            file_path=save_path,
        )
        assert len(classifier_manager._classifiers) == 2
        loaded_classifier = classifier_manager._classifiers[loaded_classifier.classifier_id]
        assert loaded_classifier.few_shot_classifier.name == "test_classifier"

    def test_load_classifier_from_file__invalid_model_hash(
        self,
        db_session: Session,
        tmp_path: Path,
        mocker: MockerFixture,
        classifier: ClassifierEntry,
        classifier_manager: ClassifierManager,
    ) -> None:
        """Test saving a classifier to file and loading it back."""
        save_path = tmp_path / "classifier.pkl"
        classifier_manager.save_classifier_to_file(
            classifier_id=classifier.classifier_id, file_path=save_path
        )
        mocker.patch.object(
            embedding_model_resolver,
            "get_by_model_hash",
            return_value=None,
        )
        with pytest.raises(
            ValueError,
            match="No matching embedding model found for the classifier's hash:"
            f"'{classifier.few_shot_classifier.embedding_model_hash}'",
        ):
            classifier_manager.load_classifier_from_file(
                session=db_session,
                file_path=save_path,
            )

    def test_save_classifier_to_file__invalid_classifier_id(self, tmp_path: Path) -> None:
        """Test saving classifier with invalid ID."""
        classifier_manager = ClassifierManager()
        invalid_id = uuid4()
        with pytest.raises(ValueError, match=f"Classifier with ID {invalid_id} not found."):
            classifier_manager.save_classifier_to_file(
                classifier_id=invalid_id,
                file_path=tmp_path / "test.pkl",
            )

    def test_update_annotations(
        self,
        db_session: Session,
        mocker: MockerFixture,
    ) -> None:
        """Test updating training samples and history tracking."""
        classifier_manager = ClassifierManager()
        # Setup: Create a classifier first
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable()],
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[
                AnnotatedEmbedding(embedding=[0.1, 0.2, 0.3], annotation="cat"),
            ],
        )

        sample1, sample2, sample3, sample4 = uuid4(), uuid4(), uuid4(), uuid4()
        input_classes = ["cat", "dog"]
        # Create classifier
        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=input_classes,
            dataset_id=uuid4(),
        )

        # Test: Update training samples for multiple classes
        update_data = {
            "cat": [sample2, sample3],
            "dog": [sample4],
        }
        history = classifier_manager.get_annotations(classifier.classifier_id)
        assert len(history["cat"]) == 0  # No history yet
        assert len(history["dog"]) == 0  # No history yet
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations=update_data,
        )

        # Verify: Check history
        history = classifier_manager.get_annotations(classifier.classifier_id)
        assert "cat" in history
        assert "dog" in history
        assert len(history["cat"]) == 2
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations={"dog": [sample1]},
        )
        history = classifier_manager.get_annotations(classifier.classifier_id)
        assert len(history["dog"]) == 2

    def test_update_annotations__move_between_classes(
        self,
        db_session: Session,
        mocker: MockerFixture,
    ) -> None:
        """Test moving samples between classes in training history."""
        classifier_manager = ClassifierManager()
        # Setup: Create a classifier with initial samples
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable()],
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[
                AnnotatedEmbedding(embedding=[0.1, 0.2, 0.3], annotation="cat"),
                AnnotatedEmbedding(embedding=[0.4, 0.5, 0.6], annotation="dog"),
            ],
        )
        input_classes = ["cat", "dog"]
        sample1, sample2 = uuid4(), uuid4()
        initial_data = {
            "cat": [sample1],
            "dog": [sample2],
        }

        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=input_classes,
            dataset_id=uuid4(),
        )
        # Test: Add initial data.
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations=initial_data,
        )
        # Test: Move samples between classes.
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            # Move sample1 from cat to dog.
            new_annotations={"dog": [sample1, sample2]},
        )

        # Verify: Check history.
        history = classifier_manager.get_annotations(classifier.classifier_id)
        assert "cat" in history
        assert "dog" in history
        assert len(history["cat"]) == 0  # Sample1 moved from cat.
        assert len(history["dog"]) == 2  # Both samples now in dog.
        assert sample1 in history["dog"]
        assert sample2 in history["dog"]

    def test_update_annotations__classifier_not_found(self) -> None:
        """Test updating samples for non-existent classifier."""
        classifier_manager = ClassifierManager()
        with pytest.raises(ValueError, match="Classifier with ID .* not found"):
            classifier_manager.update_classifiers_annotations(
                classifier_id=uuid4(),
                new_annotations={"class1": [uuid4()]},
            )

    def test_get_annotations(
        self, classifier: ClassifierEntry, classifier_manager: ClassifierManager
    ) -> None:
        """Test getting training history."""
        sample1, sample2 = uuid4(), uuid4()

        # Verify: Check initial history
        history = classifier_manager.get_annotations(classifier.classifier_id)
        assert "class1" in history
        assert len(history["class1"]) == 2
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations={"class1": [sample1, sample2]},
        )
        # Verify: Check updated history
        history = classifier_manager.get_annotations(classifier.classifier_id)
        assert "class1" in history
        assert len(history["class1"]) == 4

    def test_annotations__new_class(
        self, classifier: ClassifierEntry, classifier_manager: ClassifierManager
    ) -> None:
        """Test updating training data with new class."""
        sample1, sample2 = uuid4(), uuid4()
        with pytest.raises(
            ValueError,
            match="Cannot add new classes {'dog'} to existing"
            " classifier. Allowed classes are: {'class1'}",
        ):
            classifier_manager.update_classifiers_annotations(
                classifier_id=classifier.classifier_id,
                new_annotations={
                    "dog": [sample1, sample2],
                },
            )

    def test_get_samples_for_fine_tuning(
        self,
        db_session: Session,
        fine_tuning_embeddings: list[SampleEmbeddingTable],
        mocker: MockerFixture,
    ) -> None:
        """Test creating a new classifier."""
        classifier_manager = ClassifierManager()

        mocker.patch.object(
            embedding_model_resolver,
            "get_by_model_hash",
            return_value=EmbeddingModelTable(),
        )
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable()],
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[
                AnnotatedEmbedding(embedding=[1.0, 1.0, 1.0], annotation="positive"),
                AnnotatedEmbedding(embedding=[1.0, 0.9, 0.8], annotation="positive"),
                AnnotatedEmbedding(embedding=[0.9, 0.9, 0.8], annotation="positive"),
                AnnotatedEmbedding(embedding=[0.1, 0.1, 0.1], annotation="negative"),
                AnnotatedEmbedding(embedding=[0.1, 0.1, 0.2], annotation="negative"),
                AnnotatedEmbedding(embedding=[0.1, 0.3, 0.1], annotation="negative"),
            ],
        )
        # Create input data with two classes.
        mock_input_data: dict[str, list[UUID]] = {
            "positive": [],
            "negative": [],
        }

        # Create classifier
        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=["negative", "positive"],
            dataset_id=uuid4(),
        )
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations=mock_input_data,
        )
        classifier_manager.train_classifier(
            session=db_session, classifier_id=classifier.classifier_id
        )
        classifier_manager.commit_temp_classifier(classifier.classifier_id)

        mocker.patch.object(
            sample_embedding_resolver,
            "get_all_by_dataset_id",
            return_value=fine_tuning_embeddings,
        )
        # Get samples for fine-tuning
        result = classifier_manager.get_samples_for_fine_tuning(
            session=db_session, dataset_id=uuid4(), classifier_id=classifier.classifier_id
        )

        # Verify results
        assert len(result["positive"]) == HIGH_CONFIDENCE_SAMPLES_NEEDED
        assert len(result["negative"]) == LOW_CONFIDENCE_SAMPLES_NEEDED

    def test_get_samples_for_fine_tuning__not_enough_samples(
        self,
        db_session: Session,
        mocker: MockerFixture,
    ) -> None:
        """Test creating a new classifier."""
        classifier_manager = ClassifierManager()

        mocker.patch.object(
            embedding_model_resolver,
            "get_by_model_hash",
            return_value=EmbeddingModelTable(),
        )
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable()],
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[
                AnnotatedEmbedding(embedding=[1.0, 1.0, 1.0], annotation="positive"),
                AnnotatedEmbedding(embedding=[1.0, 0.9, 0.8], annotation="positive"),
                AnnotatedEmbedding(embedding=[0.1, 0.1, 0.2], annotation="negative"),
                AnnotatedEmbedding(embedding=[0.1, 0.3, 0.1], annotation="negative"),
            ],
        )
        # Create input data with two classes.
        mock_input_data: dict[str, list[UUID]] = {
            "positive": [],
            "negative": [],
        }

        # Create classifier
        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=["positive", "negative"],
            dataset_id=uuid4(),
        )
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations=mock_input_data,
        )
        classifier_manager.train_classifier(
            session=db_session, classifier_id=classifier.classifier_id
        )
        classifier_manager.commit_temp_classifier(classifier.classifier_id)
        # Mock the sample resolver to return a list of samples
        # Create input data with two classes. Add 20 samples that will provide
        # low confidence.
        input_embeddings = [
            SampleEmbeddingTable(sample_id="0", embedding=[0.2, 0.2, 0.2]) for _ in range(20)
        ]
        # Add 1 sample that will provide high confidence.
        input_embeddings.append(SampleEmbeddingTable(sample_id="1", embedding=[0.95, 0.95, 0.95]))
        mocker.patch.object(
            sample_embedding_resolver,
            "get_all_by_dataset_id",
            return_value=input_embeddings,
        )
        # Get samples for fine-tuning
        result = classifier_manager.get_samples_for_fine_tuning(
            session=db_session, dataset_id=uuid4(), classifier_id=classifier.classifier_id
        )

        # Verify results
        # As we have less than HIGH_CONFIDENCE_SAMPLES_NEEDED the result will
        # contain only one positive sample.
        assert len(result["positive"]) == 1
        assert len(result["negative"]) == LOW_CONFIDENCE_SAMPLES_NEEDED

    def test_get_all_classifiers(
        self,
        db_session: Session,
        mocker: MockerFixture,
    ) -> None:
        """Test creating a new classifier."""
        classifier_manager = ClassifierManager()
        mocker.patch.object(
            embedding_model_resolver,
            "get_all_by_dataset_id",
            return_value=[EmbeddingModelTable(embedding_model_hash="mock_hash")],
        )
        mocker.patch.object(
            embedding_model_resolver,
            "get_by_model_hash",
            return_value=EmbeddingModelTable(),
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[AnnotatedEmbedding(embedding=[0.1, 0.2, 0.3], annotation="class1")],
        )
        input_clases = ["class1"]
        # Create classifier.
        classifier = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier",
            class_list=input_clases,
            dataset_id=uuid4(),
        )
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier.classifier_id,
            new_annotations={
                "class1": [uuid4(), uuid4()],
            },
        )
        classifier_manager.train_classifier(
            session=db_session, classifier_id=classifier.classifier_id
        )
        classifier_manager.commit_temp_classifier(classifier.classifier_id)
        input_clases = ["another_class"]
        classifier2 = classifier_manager.create_classifier(
            session=db_session,
            name="test_classifier_v2",
            class_list=input_clases,
            dataset_id=uuid4(),
        )
        classifier_manager.update_classifiers_annotations(
            classifier_id=classifier2.classifier_id,
            new_annotations={
                "another_class": [uuid4(), uuid4()],
            },
        )
        mocker.patch.object(
            few_shot_classifier.classifier_manager,
            "_create_annotated_embeddings",
            return_value=[
                AnnotatedEmbedding(embedding=[0.1, 0.2, 0.3], annotation="another_class")
            ],
        )
        classifier_manager.train_classifier(
            session=db_session, classifier_id=classifier2.classifier_id
        )
        classifier_manager.commit_temp_classifier(classifier2.classifier_id)
        classifiers = classifier_manager.get_all_classifiers()
        assert len(classifiers) == 2
        assert classifiers[0].classifier_name == "test_classifier"
        assert classifiers[1].classifier_name == "test_classifier_v2"
        assert classifiers[0].classifier_id == classifier.classifier_id
        assert classifiers[1].classifier_id == classifier2.classifier_id
        assert classifiers[0].class_list == ["class1"]
        assert classifiers[1].class_list == ["another_class"]

    def test_run_classifier(
        self,
        db_session: Session,
        samples: list[ImageTable],
        mocker: MockerFixture,
        classifier: ClassifierEntry,
        embedding_model: EmbeddingModelTable,
    ) -> None:
        """Test run function of a classifier."""
        classifier_manager = ClassifierManager()
        classifier_manager._classifiers[classifier.classifier_id] = classifier
        dataset_id = samples[0].dataset_id

        # Check that we have no existing classification annotations.
        annotations = annotation_resolver.get_all(
            session=db_session,
            filters=AnnotationsFilter(annotation_types=[AnnotationType.CLASSIFICATION]),
        ).annotations
        assert not annotations

        mocker.patch.object(
            RandomForest,
            "predict",
            return_value=[
                [0.1, 0.0],
                [0.2, 0.0],
                [0.3, 0.0],
                [0.4, 0.0],
                [0.5, 0.0],
                [0.6, 0.0],
                [0.7, 0.0],
                [0.8, 0.0],
                [0.9, 0.0],
                [0.91, 0.0],
            ],
        )
        # create dummy embeddings for the samples.
        sample_embedding_resolver.create_many(
            session=db_session,
            sample_embeddings=[
                SampleEmbeddingCreate(
                    sample_id=sample.sample_id,
                    embedding=[0.1, 0.2, 0.3],
                    embedding_model_id=embedding_model.embedding_model_id,
                )
                for sample in samples
            ],
        )

        classifier_manager.run_classifier(
            session=db_session,
            classifier_id=classifier.classifier_id,
            dataset_id=dataset_id,
        )
        # Check that we have created 10 classification annotations.
        annotations = annotation_resolver.get_all(
            session=db_session,
            filters=AnnotationsFilter(annotation_types=[AnnotationType.CLASSIFICATION]),
        ).annotations

        assert len(annotations) == 10
        # Store one annotation to check it is updated correctly.
        annotation_sample_id = annotations[0].sample_id
        assert annotations[0].confidence is not None
        assert np.isclose(annotations[0].confidence, 0.1)

        # Run the classifier again to check that it does not create duplicates
        # and updates the existing annotations.
        mocker.patch.object(
            RandomForest,
            "predict",
            return_value=[
                [0.15, 0.0],
                [0.25, 0.0],
                [0.35, 0.0],
                [0.45, 0.0],
                [0.55, 0.0],
                [0.65, 0.0],
                [0.75, 0.0],
                [0.85, 0.0],
                [0.95, 0.0],
                [0.96, 0.0],
            ],
        )

        classifier_manager.run_classifier(
            session=db_session,
            classifier_id=classifier.classifier_id,
            dataset_id=dataset_id,
        )
        annotations_updated = annotation_resolver.get_all(
            session=db_session,
            filters=AnnotationsFilter(annotation_types=[AnnotationType.CLASSIFICATION]),
        ).annotations
        # Check that we have no new annotations and the existing
        # annotations are updated.
        assert len(annotations_updated) == 10
        assert annotations_updated[0].sample_id == annotation_sample_id
        assert annotations_updated[0].confidence is not None
        assert np.isclose(annotations_updated[0].confidence, 0.15)
        assert (
            annotations_updated[0].annotation_label.annotation_label_name
            == "test_classifier_class1"
        )

    def test_run_classifier__no_samples_in_database(
        self,
        db_session: Session,
        samples: list[ImageTable],
        mocker: MockerFixture,
        classifier: ClassifierEntry,
        classifier_manager: ClassifierManager,
    ) -> None:
        """Test run function of a classifier."""
        dataset_id = samples[0].dataset_id

        # Check that we have no existing classification annotations.
        annotations = annotation_resolver.get_all(
            session=db_session,
            filters=AnnotationsFilter(annotation_types=[AnnotationType.CLASSIFICATION]),
        ).annotations
        assert not annotations

        mocker.patch.object(
            RandomForest,
            "predict",
            return_value=[],
        )
        with pytest.raises(
            ValueError,
            match="Predict returned empty list for classifier:",
        ):
            classifier_manager.run_classifier(
                session=db_session,
                classifier_id=classifier.classifier_id,
                dataset_id=dataset_id,
            )
