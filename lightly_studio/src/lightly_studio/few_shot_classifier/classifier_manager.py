"""ClassifierManager implementation."""

from __future__ import annotations

import copy
import io
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from random import sample
from uuid import UUID, uuid4

from sqlmodel import Session

from lightly_studio.few_shot_classifier import random_forest_classifier
from lightly_studio.few_shot_classifier.classifier import (
    AnnotatedEmbedding,
    ExportType,
)
from lightly_studio.few_shot_classifier.random_forest_classifier import (
    RandomForest,
)
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
)
from lightly_studio.models.classifier import EmbeddingClassifier
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
)

HIGH_CONFIDENCE_THRESHOLD = 0.5
LOW_CONFIDENCE_THRESHOLD = 0.5

HIGH_CONFIDENCE_SAMPLES_NEEDED = 10
LOW_CONFIDENCE_SAMPLES_NEEDED = 10

FSC_ANNOTATION_TASK_PREFIX = "FSC_"


class ClassifierManagerProvider:
    """Provider for the ClassifierManager singleton instance."""

    _instance: ClassifierManager | None = None

    @classmethod
    def get_classifier_manager(cls) -> ClassifierManager:
        """Get the singleton instance of ClassifierManager.

        Returns:
            The singleton instance of ClassifierManager.

        Raises:
            ValueError: If no instance exists and no session is provided.
        """
        if cls._instance is None:
            cls._instance = ClassifierManager()
        return cls._instance


@dataclass
class ClassifierEntry:
    """Classifier dataclass."""

    classifier_id: UUID

    # TODO(Horatiu, 05/2025): Use FewShotClassifier instead of RandomForest
    #  when the interface is ready. Add method to get classifier info.
    few_shot_classifier: RandomForest

    # Annotations history is used to keep track of the samples that have
    # been used for training. It is a dictionary with the key the class name and
    # the value a list of sample IDs that belong to that class.
    # This is used to avoid using the same samples for fine tuning multiple
    # times.
    annotations: dict[str, list[UUID]]

    # Inactive classifiers are used for handling the fine tuning process.
    # From the moment the classifier is created untill it is saved is_active
    # will be false.
    is_active: bool = False

    annotation_label_ids: list[UUID] | None = None


class ClassifierManager:
    """ClassifierManager class.

    This class manages the lifecycle of a few-shot classifier,
    including training, exporting, and loading the classifier.
    """

    def __init__(self) -> None:
        """Initialize the ClassifierManager."""
        self._classifiers: dict[UUID, ClassifierEntry] = {}

    def create_classifier(
        self,
        session: Session,
        name: str,
        class_list: list[str],
        collection_id: UUID,
    ) -> ClassifierEntry:
        """Create a new classifier.

        Args:
            session: Database session for resolver operations.
            name: The name of the classifier.
            class_list: List of classes to be used for training.
            collection_id: The collection_id to which the samples belong.

        Returns:
            The created classifier name and ID.
        """
        embedding_models = embedding_model_resolver.get_all_by_collection_id(
            session=session,
            collection_id=collection_id,
        )
        if len(embedding_models) == 0:
            raise ValueError("No embedding model found for the given collection ID.")
        # TODO(Horatiu, 05/2025): Handle multiple models correctly when
        # available
        if len(embedding_models) > 1:
            raise ValueError("Multiple embedding models found for the given collection ID.")
        embedding_model = embedding_models[0]
        classifier = RandomForest(
            name=name,
            classes=class_list,
            embedding_model_hash=embedding_model.embedding_model_hash,
            embedding_model_name=embedding_model.name,
        )

        classifier_id = uuid4()
        self._classifiers[classifier_id] = ClassifierEntry(
            classifier_id=classifier_id,
            few_shot_classifier=classifier,
            is_active=False,
            annotations={class_name: [] for class_name in class_list},
        )

        return self._classifiers[classifier_id]

    def train_classifier(self, session: Session, classifier_id: UUID) -> None:
        """Train the classifier.

        Args:
            session: Database session for resolver operations.
            classifier_id: The ID of the classifier to train.

        Raises:
            ValueError: If the classifier with the given ID does not exist.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")

        embedding_model = embedding_model_resolver.get_by_model_hash(
            session=session,
            embedding_model_hash=classifier.few_shot_classifier.embedding_model_hash,
        )
        if embedding_model is None:
            raise ValueError(
                "No embedding model found for hash '"
                f"{classifier.few_shot_classifier.embedding_model_hash}'"
            )

        # Get annotations.
        annotations = classifier.annotations
        annotated_embeddings = _create_annotated_embeddings(
            session=session,
            class_to_sample_ids=annotations,
            embedding_model_id=embedding_model.embedding_model_id,
        )
        # Train the classifier with the annotated embeddings.
        # This will overwrite the previous training.
        classifier.few_shot_classifier.train(annotated_embeddings)

    def commit_temp_classifier(self, classifier_id: UUID) -> None:
        """Set the classifier as active.

        Args:
            classifier_id: The ID of the classifier to save.

        Raises:
            ValueError: If the classifier with the given ID does not exist
            or if the classifier is not yet trained.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")
        if classifier.few_shot_classifier.is_trained() is False:
            raise ValueError(f"Classifier with ID {classifier_id} is not trained yet.")
        classifier.is_active = True

    def drop_temp_classifier(self, classifier_id: UUID) -> None:
        """Remove a classifier that is inactive.

        Args:
            classifier_id: The ID of the classifier to drop.

        Raises:
            ValueError: If the classifier with the given ID does not exist.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")
        if classifier.is_active:
            raise ValueError(f"Classifier with ID {classifier_id} is active and cannot be dropped.")
        self._classifiers.pop(classifier_id, None)

    def save_classifier_to_file(self, classifier_id: UUID, file_path: Path) -> None:
        """Save the classifier to file.

        Args:
            classifier_id: The ID of the classifier to save.
            file_path: The path to save the classifer to.

        Raises:
            ValueError: If the classifier with the given ID does not exist.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")
        if not classifier.is_active:
            raise ValueError(
                f"Classifier with ID {classifier_id} is not active and cannot be saved."
            )
        classifier.few_shot_classifier.export(export_path=file_path, export_type="sklearn")

    def load_classifier_from_file(self, session: Session, file_path: Path) -> ClassifierEntry:
        """Loads a classifier from file.

        Args:
            session: Database session for resolver operations.
            file_path: The path from where to load the classifier.

        Returns:
            The ID of the loaded classifier.
        """
        classifier = random_forest_classifier.load_random_forest_classifier(
            classifier_path=file_path, buffer=None
        )
        embedding_model = embedding_model_resolver.get_by_model_hash(
            session=session,
            embedding_model_hash=classifier.embedding_model_hash,
        )
        if embedding_model is None:
            raise ValueError(
                "No matching embedding model found for the classifier's hash:"
                f"'{classifier.embedding_model_hash}'."
            )

        classifier_id = uuid4()
        self._classifiers[classifier_id] = ClassifierEntry(
            classifier_id=classifier_id,
            few_shot_classifier=classifier,
            is_active=True,
            annotations={class_name: [] for class_name in classifier.classes},
        )
        return self._classifiers[classifier_id]

    def provide_negative_samples(
        self, session: Session, collection_id: UUID, selected_samples: list[UUID], limit: int = 10
    ) -> Sequence[ImageTable]:
        """Provide random samples that are not in the selected samples.

        Args:
            session: Database session for resolver operations.
            collection_id: The collection_id to pull samples from.
            selected_samples: List of sample UUIDs to exclude.
            limit: Number of negative samples to return.

        Returns:
            List of negative samples.

        """
        return image_resolver.get_samples_excluding(
            session=session,
            collection_id=collection_id,
            excluded_sample_ids=selected_samples,
            limit=limit,
        )

    def update_classifiers_annotations(
        self,
        classifier_id: UUID,
        new_annotations: dict[str, list[UUID]],
    ) -> None:
        """Update annotations with new samples for multiple classes.

        Args:
            classifier_id: The ID of the classifier.
            new_annotations: Dictionary mapping class names to lists of sample
            IDs.

        Raises:
            ValueError: If the classifier doesn't exist.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")

        annotations = classifier.annotations
        # Validate no new classes are being added.
        if not set(new_annotations.keys()).issubset(annotations.keys()):
            invalid_classes = set(new_annotations.keys()) - set(annotations.keys())
            raise ValueError(
                f"Cannot add new classes {invalid_classes} to existing"
                f" classifier. Allowed classes are: {set(annotations.keys())}"
            )

        # Get all new samples that will be added.
        all_new_samples = {
            sample_id for samples in new_annotations.values() for sample_id in samples
        }

        # Update annotations.
        for existing_class in annotations:
            # Remove newly annotated samples if existing already
            # and add samples for this class.
            new_class_samples = set(new_annotations.get(existing_class, []))
            annotations[existing_class] = list(
                (set(annotations[existing_class]) - all_new_samples) | new_class_samples
            )

    def get_annotations(self, classifier_id: UUID) -> dict[str, list[UUID]]:
        """Get all samples used in training for each class.

        Args:
            classifier_id: The ID of the classifier.

        Returns:
            Dictionary mapping class names to lists of sample IDs.

        Raises:
            ValueError: If the classifier doesn't exist.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")

        return copy.deepcopy(classifier.annotations)

    def get_samples_for_fine_tuning(
        self, session: Session, collection_id: UUID, classifier_id: UUID
    ) -> dict[str, list[UUID]]:
        """Get samples for fine-tuning the classifier.

        Gets at most 20 samples total:
        - 10 positive samples (prediction confidence > 0.5)
        - 10 uncertain samples (prediction confidence < 0.5)
        If there are not enough samples, it will return all available
        samples of that type.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of the collection to pull samples from.
            classifier_id: The ID of the classifier to use.

        Returns:
            Dictionary mapping class names to sample IDs. The first class from
            classifier.classes gets samples with high confidence predictions,
            the second class gets samples with low confidence predictions.

        Raises:
            ValueError: If the classifier with the given ID does not exist
            or there is no appropriate embedding model.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")
        # Get all previously used annotations.
        annotations = classifier.annotations
        used_samples = {sample_id for samples in annotations.values() for sample_id in samples}

        embedding_model = embedding_model_resolver.get_by_model_hash(
            session=session,
            embedding_model_hash=classifier.few_shot_classifier.embedding_model_hash,
        )
        if embedding_model is None:
            raise ValueError(
                "No embedding model found for hash '"
                f"{classifier.few_shot_classifier.embedding_model_hash}'"
            )

        # Create list of SampleEmbedding objects to track sample IDs
        sample_embeddings = sample_embedding_resolver.get_all_by_collection_id(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
        )

        # Get predictions for all embeddings.
        embeddings = [se.embedding for se in sample_embeddings]
        predictions = classifier.few_shot_classifier.predict(embeddings)

        # Group samples by prediction confidence.
        high_conf = []  # > 0.5
        low_conf = []  # <= 0.5

        for sample_embedding, pred in zip(sample_embeddings, predictions):
            if sample_embedding.sample_id in used_samples:
                continue
            if pred[0] > HIGH_CONFIDENCE_THRESHOLD:
                high_conf.append(sample_embedding.sample_id)
            elif pred[0] <= LOW_CONFIDENCE_THRESHOLD:
                low_conf.append(sample_embedding.sample_id)

        return {
            classifier.few_shot_classifier.classes[0]: sample(
                high_conf, min(len(high_conf), HIGH_CONFIDENCE_SAMPLES_NEEDED)
            ),
            classifier.few_shot_classifier.classes[1]: sample(
                low_conf, min(len(low_conf), LOW_CONFIDENCE_SAMPLES_NEEDED)
            ),
        }

    def run_classifier(self, session: Session, classifier_id: UUID, collection_id: UUID) -> None:
        """Run the classifier on the collection.

        Args:
            session: Database session for resolver operations.
            classifier_id: The ID of the classifier to run.
            collection_id: The ID of the collection to run the classifier on.

        Raises:
            ValueError: If the classifier with the given ID does not exist
            or there is no appropriate embedding model.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")

        if not classifier.is_active:
            raise ValueError(
                f"Classifier with ID {classifier_id} is not active and cannot be used."
            )
        embedding_model = embedding_model_resolver.get_by_model_hash(
            session=session,
            embedding_model_hash=classifier.few_shot_classifier.embedding_model_hash,
        )
        if embedding_model is None:
            raise ValueError(
                "No embedding model found for hash '"
                f"{classifier.few_shot_classifier.embedding_model_hash}'"
            )

        # Create list of SampleEmbedding objects to track sample IDs
        sample_embeddings = sample_embedding_resolver.get_all_by_collection_id(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
        )

        # Extract just the embeddings for prediction
        embeddings = [se.embedding for se in sample_embeddings]
        predictions = classifier.few_shot_classifier.predict(embeddings)
        if len(predictions):
            _create_annotation_labels_for_classifier(
                session=session,
                collection_id=collection_id,
                classifier=classifier,
            )
        else:
            raise ValueError(f"Predict returned empty list for classifier:'{classifier_id}'")
        # Check if annotation labels are available
        if not classifier.annotation_label_ids:
            raise ValueError(f"Classifier with ID '{classifier_id}' has no annotation labels")

        # For each prediction add a classification annotation for the
        # sample or update an existing one.
        classification_annotations = []
        for sample_embedding, prediction in zip(sample_embeddings, predictions):
            max_index = prediction.index(max(prediction))
            classification_annotations.append(
                AnnotationCreate(
                    parent_sample_id=sample_embedding.sample_id,
                    annotation_label_id=classifier.annotation_label_ids[max_index],
                    annotation_type=AnnotationType.CLASSIFICATION,
                    confidence=prediction[max_index],
                )
            )
        #  Clear previous annotations by this classifier
        annotation_resolver.delete_annotations(
            session=session,
            annotation_label_ids=classifier.annotation_label_ids,
        )
        annotation_resolver.create_many(
            session=session,
            parent_collection_id=collection_id,
            annotations=classification_annotations,
        )

    def get_all_classifiers(self) -> list[EmbeddingClassifier]:
        """Get all active classifiers.

        Returns:
            List of EmbeddingClassifier objects representing active classifiers.
        """
        return [
            EmbeddingClassifier(
                classifier_name=classifier.few_shot_classifier.name,
                classifier_id=classifier.classifier_id,
                class_list=classifier.few_shot_classifier.classes,
            )
            for classifier in self._classifiers.values()
            if classifier.is_active
        ]

    def get_classifier_by_id(self, classifier_id: UUID) -> EmbeddingClassifier:
        """Get all active classifiers.

        Args:
            classifier_id: The ID of the classifier to get.

        Raises:
            ValueError: If the classifier with the given ID does not exist.

        Returns:
            EmbeddingClassifier object.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")
        return EmbeddingClassifier(
            classifier_name=classifier.few_shot_classifier.name,
            classifier_id=classifier_id,
            class_list=classifier.few_shot_classifier.classes,
        )

    def save_classifier_to_buffer(
        self, classifier_id: UUID, buffer: io.BytesIO, export_type: ExportType
    ) -> None:
        """Save the classifier to a buffer.

        Args:
            classifier_id: The ID of the classifier to save.
            buffer: The buffer to save the classifier to.
            export_type: The type of export to perform.

        Raises:
            ValueError: If the classifier with the given ID does not exist.
        """
        classifier = self._classifiers.get(classifier_id)
        if classifier is None:
            raise ValueError(f"Classifier with ID {classifier_id} not found.")
        classifier.few_shot_classifier.export(buffer=buffer, export_type=export_type)

    def load_classifier_from_buffer(self, session: Session, buffer: io.BytesIO) -> ClassifierEntry:
        """Loads a classifier from a buffer.

        Args:
            session: Database session for resolver operations.
            buffer: The buffer containing the classifier data.

        Returns:
            The ID of the loaded classifier.

        Raises:
            ValueError: If no matching embedding model is found for the
            classifier.
        """
        classifier = random_forest_classifier.load_random_forest_classifier(
            buffer=buffer, classifier_path=None
        )
        embedding_model = embedding_model_resolver.get_by_model_hash(
            session=session,
            embedding_model_hash=classifier.embedding_model_hash,
        )
        if embedding_model is None:
            raise ValueError(
                "No matching embedding model found for the classifier's hash: "
                f"'{classifier.embedding_model_hash}'."
            )

        classifier_id = uuid4()
        self._classifiers[classifier_id] = ClassifierEntry(
            classifier_id=classifier_id,
            few_shot_classifier=classifier,
            is_active=True,
            annotations={class_name: [] for class_name in classifier.classes},
        )
        return self._classifiers[classifier_id]


def _create_annotation_labels_for_classifier(
    session: Session,
    collection_id: UUID,
    classifier: ClassifierEntry,
) -> None:
    """Create annotation labels for the classifier.

    Args:
        session: Database session.
        collection_id: The collection ID to which the samples belong.
        classifier: The classifier object to update.
    """
    dataset_id = collection_resolver.get_dataset(
        session=session, collection_id=collection_id
    ).collection_id
    # Check if the annotation label with the classifier name and class
    # names exists and if not create it.
    if classifier.annotation_label_ids is None:
        annotation_label_ids = []
        for class_name in classifier.few_shot_classifier.classes:
            annotation_label = annotation_label_resolver.create(
                session=session,
                label=AnnotationLabelCreate(
                    dataset_id=dataset_id,
                    annotation_label_name=classifier.few_shot_classifier.name + "_" + class_name,
                ),
            )
            annotation_label_ids.append(annotation_label.annotation_label_id)
        classifier.annotation_label_ids = annotation_label_ids


def _create_annotated_embeddings(
    session: Session,
    class_to_sample_ids: dict[str, list[UUID]],
    embedding_model_id: UUID,
) -> list[AnnotatedEmbedding]:
    """Create annotated embeddings from input data.

    Args:
        session: Database session.
        class_to_sample_ids: Dictionary mapping class names to sample UUIDs.
        embedding_model_id: The embedding model ID to filter by.

    Returns:
        List of annotated embeddings for training.
    """
    return [
        AnnotatedEmbedding(embedding=embedding.embedding, annotation=class_name)
        for class_name, sample_uuids in class_to_sample_ids.items()
        for embedding in sample_embedding_resolver.get_by_sample_ids(
            session=session,
            sample_ids=sample_uuids,
            embedding_model_id=embedding_model_id,
        )
    ]
