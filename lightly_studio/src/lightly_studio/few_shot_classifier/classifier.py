"""FewShotClassifier Protocol."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

ExportType = Literal["sklearn", "lightly"]


@dataclass
class AnnotatedEmbedding:
    """Annotated embedding class.

    Attributes:
        embedding: The embedding vector as a list of floats.
        annotation: The annotation for the embedding.
                    Note: Currently it is an string but it can be a integer or
                    any other type.
    """

    embedding: list[float]
    annotation: str


@runtime_checkable
class FewShotClassifier(Protocol):
    """Protocol defining the interface for classifiers."""

    def train(self, annotated_embeddings: list[AnnotatedEmbedding]) -> None:
        """Trains a classifier using the provided input.

        Args:
            annotated_embeddings: A list of annotated embeddings to train the
            classifier.

        Raises:
            ValueError: If annotated_embeddings is empty or contains invalid
            classes.
        """
        ...

    def predict(self, embeddings: list[list[float]]) -> list[list[float]]:
        """Predicts the classification scores for a list of embeddings.

        Args:
            embeddings: A list of embeddings, where each embedding is a list of
            floats.

        Returns:
            A list of lists, where each inner list represents the probability
            distribution over classes for the corresponding input embedding.
            Each value in the inner list corresponds to the likelihood of the
            embedding belonging to a specific class.
            If embeddings is empty, returns an empty list.
        """
        ...

    def export(
        self,
        export_path: Path | None,
        buffer: io.BytesIO | None,
        export_type: ExportType,
    ) -> None:
        """Exports the classifier to a specified file.

        This method saves the trained classifier to the given file path so that
        it can be reused or shared.

        Args:
            export_path: The path to the file where the classifier should
            be saved.
            buffer: An optional in-memory buffer to write the exported
            classifier to.
            export_type: The type of export format to use. This can be either
            "sklearn_instance" or "raw".
        """
        ...
