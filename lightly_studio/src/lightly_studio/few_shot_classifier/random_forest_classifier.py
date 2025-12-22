"""RandomForest classifier implementations."""

from __future__ import annotations

import io
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn  # type: ignore[import-untyped]
from sklearn.ensemble import (  # type: ignore[import-untyped]
    RandomForestClassifier,
)
from sklearn.tree import (  # type: ignore[import-untyped]
    DecisionTreeClassifier,
)
from sklearn.utils import validation  # type: ignore[import-untyped]
from typing_extensions import assert_never

from .classifier import AnnotatedEmbedding, ExportType, FewShotClassifier

# The version of the file format used for exporting and importing classifiers.
# This is used to ensure compatibility between different versions of the code.
# If the format changes, this version should be incremented.
FILE_FORMAT_VERSION = "1.0.0"


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
    embedding_model_hash: str
    embedding_model_name: str
    sklearn_version: str


@dataclass
class InnerNode:
    """Inner node of a decision tree.

    Defaults are used for tree construction.
    """

    feature_index: int = 0
    threshold: float = 0.0
    left_child: int = 0
    right_child: int = 0


@dataclass
class LeafNode:
    """Leaf node of a decision tree."""

    class_probabilities: list[float]


@dataclass
class ExportedTree:
    """Exported tree structure."""

    inner_nodes: list[InnerNode]
    leaf_nodes: list[LeafNode]


@dataclass
class RandomForestExport:
    """Datastructure for exporting the RandomForest model."""

    metadata: ModelExportMetadata
    trees: list[ExportedTree]


class RandomForest(FewShotClassifier):
    """RandomForest classifier."""

    def __init__(
        self,
        name: str,
        classes: list[str],
        embedding_model_name: str,
        embedding_model_hash: str,
    ) -> None:
        """Initialize the RandomForestClassifier with predefined classes.

        Args:
            name: Name of the classifier.
            classes: Ordered list of class labels that will be used for training
                and predictions. The order of this list determines the order of
                probability values in predictions.
            embedding_model_name: Name of the model used for creating the
                embeddings.
            embedding_model_hash: Hash of the model used for creating the
                embeddings.
            Note: embedding_model_name and embedding_model_hash are used for
            traceability in the exported model metadata.

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
        self._embedding_model_name = embedding_model_name
        self.embedding_model_hash = embedding_model_hash

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
        export_type: ExportType = "sklearn",
    ) -> None:
        """Exports the classifier to a specified file.

        Args:
            export_path: The full file path where the export will be saved.
            buffer: A BytesIO buffer to save the export to.
            export_type: The type of export. Options are:
                "sklearn": Exports the RandomForestClassifier instance.
                "lightly": Exports the model in raw format with metadata
                and tree details.
        """
        metadata = ModelExportMetadata(
            name=self.name,
            file_format_version=FILE_FORMAT_VERSION,
            model_type="RandomForest",
            created_at=str(datetime.now(timezone.utc).isoformat()),
            class_names=self.classes,
            num_input_features=self._model.n_features_in_,
            num_estimators=len(self._model.estimators_),
            embedding_model_hash=self.embedding_model_hash,
            embedding_model_name=self._embedding_model_name,
            sklearn_version=sklearn.__version__,
        )

        if export_type == "sklearn":
            # Combine the model and metadata into a single dictionary
            export_data = {
                "model": self._model,
                "metadata": metadata,
            }

            if buffer is not None:
                pickle.dump(export_data, buffer)
            elif export_path is not None:
                # Save to the specified file path.
                # Ensure parent dirs exist.
                export_path.parent.mkdir(parents=True, exist_ok=True)
                with open(export_path, "wb") as f:
                    pickle.dump(export_data, f)

        elif export_type == "lightly":
            export_data_raw = _export_random_forest_model(
                model=self._model,
                metadata=metadata,
                all_classes=self.classes,
            )
            if buffer is not None:
                pickle.dump(export_data_raw, buffer)
            elif export_path is not None:
                # Save to the specified file path.
                # Ensure parent dirs exist.
                export_path.parent.mkdir(parents=True, exist_ok=True)
                with open(export_path, "wb") as f:
                    pickle.dump(export_data_raw, f)
        else:
            assert_never(export_type)

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
        embedding_model_hash=metadata.embedding_model_hash,
    )
    # Set the model.
    instance._model = model  # noqa: SLF001
    return instance


def _export_random_forest_model(
    model: RandomForestClassifier,
    metadata: ModelExportMetadata,
    all_classes: list[str],
) -> RandomForestExport:
    """Converts a sk-learn RandomForestClassifier to RandomForestExport format.

    Args:
        model: The trained random forest model to export.
        metadata: Metadata describing the collection and training setup.
        all_classes: Full list of all class labels.

    Returns:
        RandomForestExport: The serialized export object containing all trees
            and metadata.
    """
    trained_classes: list[int] = model.classes_
    trees = [_export_single_tree(tree, trained_classes, all_classes) for tree in model.estimators_]
    return RandomForestExport(metadata=metadata, trees=trees)


def load_lightly_random_forest(path: Path | None, buffer: io.BytesIO | None) -> RandomForestExport:
    """Loads a Lightly exported RandomForest model from a file or buffer.

    Args:
        path: The path to the exported classifier file.
        buffer: A BytesIO buffer containing the exported classifier.
    If both path and buffer are provided, the path will be used.

    Returns:
        A RandomForestExport instance.

    Raises:
        ValueError: If the file is not a valid RandomForestExport or
                if the version/format mismatches.
    """
    if path is not None:
        with open(path, "rb") as f:
            data = pickle.load(f)
    elif buffer is not None:
        data = pickle.load(buffer)

    if not isinstance(data, RandomForestExport):
        raise ValueError("Loaded object is not a RandomForestExport instance.")

    if data.metadata.file_format_version != FILE_FORMAT_VERSION:
        raise ValueError(
            f"File format version mismatch. Expected '{FILE_FORMAT_VERSION}', "
            f"got '{data.metadata.file_format_version}'."
        )
    return data


def predict_with_lightly_random_forest(
    model: RandomForestExport, embeddings: list[list[float]]
) -> list[list[float]]:
    """Predicts the classification scores for a list of embeddings.

    Args:
        model: A RandomForestExport instance containing the model and metadata.
        embeddings: A list of embeddings.

    Returns:
        A list of lists, where each inner list represents the probability
            distribution over classes for the corresponding input embedding.

    Raises:
        ValueError: If the provided embeddings have different size than
            expected.
    """
    expected_dim = model.metadata.num_input_features
    all_probs: list[list[float]] = []

    for embedding in embeddings:
        if len(embedding) != expected_dim:
            raise ValueError(
                f"Embedding has wrong dimensionality: expected {expected_dim},got {len(embedding)}"
            )

        tree_probs: list[list[float]] = [
            _predict_tree_probs(tree, embedding) for tree in model.trees
        ]

        mean_probs = np.mean(tree_probs, axis=0).tolist()
        all_probs.append(mean_probs)

    return all_probs


def _export_single_tree(
    tree: DecisionTreeClassifier,
    trained_classes: list[int],
    all_classes: list[str],
) -> ExportedTree:
    """Converts a single sk-learn tree into a serializable ExportedTree format.

    Args:
        tree: The decision tree to convert.
        trained_classes: Indices of the classes the tree was trained on.
        all_classes: Full list of all class labels.

    Returns:
        ExportedTree: A representation of the tree with explicit node and leaf
                    structures, compatible with the Lightly format.
    """
    tree_structure = tree.tree_
    inner_nodes: list[InnerNode] = []
    leaf_nodes: list[LeafNode] = []
    node_map = {}  # Maps node_id to (mapped_index, is_leaf)

    for node_id in range(tree_structure.node_count):
        is_leaf = tree_structure.children_left[node_id] == tree_structure.children_right[node_id]
        if is_leaf:
            leaf_idx = len(leaf_nodes)
            # value[node_id] is a 2D array of shape [1, n_classes].
            # [0] is used to extract the inner array and
            # convert it to a 1D array of class counts.
            class_weights = tree_structure.value[node_id][0]
            total = sum(class_weights)
            probs = (class_weights / total).tolist() if total > 0 else [0.0] * len(class_weights)

            # Order probabilities according to the initial classes.
            # Initialize zeros for all possible classes.
            full_probs = [0.0 for _ in range(len(all_classes))]
            # Map probabilities to their correct positions.
            for trained_class, prob in zip(trained_classes, probs):
                full_probs[trained_class] = prob

            leaf_nodes.append(LeafNode(class_probabilities=full_probs))
            node_map[node_id] = (-leaf_idx - 1, True)
        else:
            inner_idx = len(inner_nodes)
            node_map[node_id] = (inner_idx, False)
            # Reserve a spot for the inner node.
            inner_nodes.append(InnerNode())

    # Now populate inner_nodes using mapped indices.
    for node_id in range(tree_structure.node_count):
        mapped_idx, is_leaf = node_map[node_id]
        if is_leaf:
            continue

        left_id = tree_structure.children_left[node_id]
        right_id = tree_structure.children_right[node_id]
        left_mapped = node_map[left_id][0]
        right_mapped = node_map[right_id][0]

        inner_nodes[mapped_idx] = InnerNode(
            feature_index=int(tree_structure.feature[node_id]),
            threshold=float(tree_structure.threshold[node_id]),
            left_child=left_mapped,
            right_child=right_mapped,
        )

    return ExportedTree(inner_nodes=inner_nodes, leaf_nodes=leaf_nodes)


def _predict_tree_probs(tree: ExportedTree, embedding: list[float]) -> list[float]:
    """Predicts class probabilities for an embedding using a single tree.

    Args:
        tree: A ExportedTree instance used to determine the probability.
        embedding: A single embedding.

    """
    if not tree.inner_nodes:
        return tree.leaf_nodes[0].class_probabilities

    node_idx = 0  # Start at root
    while node_idx >= 0:
        node = tree.inner_nodes[node_idx]
        if embedding[node.feature_index] <= node.threshold:
            node_idx = node.left_child
        else:
            node_idx = node.right_child

    leaf_idx = -node_idx - 1
    leaf = tree.leaf_nodes[leaf_idx]
    return leaf.class_probabilities
