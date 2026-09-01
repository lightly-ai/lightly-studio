"""RandomForest classifier implementations."""

from __future__ import annotations

import io
import pickle
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn  # type: ignore[import-untyped]
from sklearn.ensemble import (  # type: ignore[import-untyped]
    RandomForestClassifier,
)
from sklearn.utils import validation  # type: ignore[import-untyped]

from lightly_studio.database.db_vector import Embedding

from .classifier import AnnotatedEmbedding, FewShotClassifier

# The version of the file format used for exporting and importing classifiers.
# This is used to ensure compatibility between different versions of the code.
# If the format changes, this version should be incremented.
FILE_FORMAT_VERSION = "1.1.0"


@dataclass
class ModelExportMetadata:
    """Metadata for exporting a model for traceability and reproducibility."""

    name: str
    file_format_version: str
    model_type: str
    created_at: str
    class_names: list[str]
    num_input_features: int
    num_estimators: int
    embedding_model_name: str
    sklearn_version: str


class RandomForest(FewShotClassifier):
    """RandomForest classifier.

    Attributes:
        name: Name of the classifier.
        classes: Ordered list of class labels used for training and predictions.
        embedding_model_name: Name of the model used for creating the embeddings.
    """

    def __init__(
        self,
        name: str,
        classes: list[str],
        embedding_model_name: str,
    ) -> None:
        """Initialize the RandomForestClassifier with predefined classes.

        Args:
            name: Name of the classifier.
            classes: Ordered list of class labels that will be used for training
                and predictions. The order of this list determines the order of
                probability values in predictions.
            embedding_model_name: Name of the model used for creating the
                embeddings.
            Note: embedding_model_name is used for traceability in the exported
            model metadata.

        Raises:
            ValueError: If classes list is empty.
        """
        if not classes:
            raise ValueError("Class list cannot be empty.")

        # Fix the random seed for reproducibility.
        self._model = RandomForestClassifier(class_weight="balanced", random_state=42)
        self.name = name
        self.classes = classes
        self._class_to_index = {label: idx for idx, label in enumerate(classes)}
        self.embedding_model_name = embedding_model_name

    def train(self, annotated_embeddings: list[AnnotatedEmbedding]) -> None:
        """Trains a classifier using the provided input.

        Args:
            annotated_embeddings: A list of annotated embeddings to train the
            classifier.

        Raises:
            ValueError: If annotated_embeddings is empty or contains invalid
            classes.
        """
        if not annotated_embeddings:
            raise ValueError("annotated_embeddings cannot be empty.")

        # Extract embeddings and labels.
        embeddings = [ae.embedding for ae in annotated_embeddings]
        labels = [ae.annotation for ae in annotated_embeddings]
        # Validate that all labels are in predefined classes.
        invalid_labels = set(labels) - set(self.classes)
        if invalid_labels:
            raise ValueError(f"Found labels not in predefined classes: {invalid_labels}")

        # Convert to NumPy arrays.
        embeddings_np = np.array(embeddings)
        labels_encoded = [self._class_to_index[label] for label in labels]

        # Train the RandomForestClassifier.
        self._model.fit(embeddings_np, labels_encoded)

    def predict(self, embeddings: Sequence[Embedding]) -> list[list[float]]:
        """Predicts the classification scores for a list of embeddings.

        Args:
            embeddings: One embedding per sample.

        Returns:
            One inner list per sample. Each inner list represents the probability
            distribution over classes for the corresponding input embedding.
            Each value in the inner list corresponds to the likelihood of the
            embedding belonging to a specific class.
            If embeddings is empty, returns an empty list.
        """
        if len(embeddings) == 0:
            return []

        # Convert embeddings to a NumPy array.
        embeddings_np = np.array(embeddings)

        # Get the classes that the model was trained on.
        trained_classes: list[int] = self._model.classes_

        # Initialize full-size probability array.
        full_probabilities = []

        # Get raw probabilities from model.
        raw_probabilities = self._model.predict_proba(embeddings_np)

        for raw_probs in raw_probabilities:
            # Initialize zeros for all possible classes.
            full_probs = [0.0 for _ in range(len(self.classes))]
            # Map probabilities to their correct positions.
            for trained_class, prob in zip(trained_classes, raw_probs):
                full_probs[trained_class] = prob
            full_probabilities.append(full_probs)
        return full_probabilities

    def export(
        self,
        export_path: Path | None = None,
        buffer: io.BytesIO | None = None,
    ) -> None:
        """Exports the classifier to a specified file.

        Args:
            export_path: The full file path where the export will be saved.
            buffer: A BytesIO buffer to save the export to.
        """
        metadata = ModelExportMetadata(
            name=self.name,
            file_format_version=FILE_FORMAT_VERSION,
            model_type="RandomForest",
            created_at=str(datetime.now(timezone.utc).isoformat()),
            class_names=self.classes,
            num_input_features=self._model.n_features_in_,
            num_estimators=len(self._model.estimators_),
            embedding_model_name=self.embedding_model_name,
            sklearn_version=sklearn.__version__,
        )

        export_data = {
            "model": self._model,
            "metadata": metadata,
        }

        if buffer is not None:
            pickle.dump(export_data, buffer)
        elif export_path is not None:
            export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(export_path, "wb") as f:
                pickle.dump(export_data, f)

    def is_trained(self) -> bool:
        """Checks if the classifier is trained.

        Returns:
            True if the classifier is trained, False otherwise.
        """
        try:
            validation.check_is_fitted(self._model)
            return True
        except sklearn.exceptions.NotFittedError:
            return False


def load_random_forest_classifier(
    classifier_path: Path | None, buffer: io.BytesIO | None
) -> RandomForest:
    """Loads a RandomForest classifier from a file or a buffer.

    Args:
        classifier_path: The path to the exported classifier file.
        buffer: A BytesIO buffer containing the exported classifier.
    If both path and buffer are provided, the path will be used.

    Returns:
        A fully initialized RandomForest classifier instance.

    Raises:
        FileNotFoundError: If the classifier_path does not exist.
        ValueError: If the file is not a valid 'sklearn' pickled export
                    or if the version/format mismatches.
    """
    if classifier_path is not None:
        if not classifier_path.exists():
            raise FileNotFoundError(f"The file {classifier_path} does not exist.")

        with open(classifier_path, "rb") as f:
            export_data = pickle.load(f)
    elif buffer is not None:
        export_data = pickle.load(buffer)

    model = export_data.get("model")
    metadata: ModelExportMetadata = export_data.get("metadata")

    if model is None or metadata is None:
        raise ValueError("The loaded file does not contain a valid model or metadata.")

    if metadata.file_format_version != FILE_FORMAT_VERSION:
        raise ValueError(
            f"File format version mismatch. Expected '{FILE_FORMAT_VERSION}', "
            f"got '{metadata.file_format_version}'."
        )
    if metadata.sklearn_version != sklearn.__version__:
        raise ValueError(
            f"File format mismatch, loading a file format for a different sklearn version. "
            f"File format uses '{metadata.sklearn_version}', got '{sklearn.__version__}'."
        )

    instance = RandomForest(
        name=metadata.name,
        classes=metadata.class_names,
        embedding_model_name=metadata.embedding_model_name,
    )
    # Set the model.
    instance._model = model  # noqa: SLF001
    return instance
