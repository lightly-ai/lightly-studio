from __future__ import annotations

import io
from pathlib import Path
from random import randint, uniform

import numpy as np
import pytest
from sklearn.utils import validation  # type: ignore[import-untyped]

from lightly_studio.few_shot_classifier.classifier import AnnotatedEmbedding
from lightly_studio.few_shot_classifier.random_forest_classifier import (
    RandomForest,
    load_lightly_random_forest,
    load_random_forest_classifier,
    predict_with_lightly_random_forest,
)


class TestRandomForestClassifier:
    """Test the RandomForest classifier."""

    def test_train(self) -> None:
        """Test the train method with valid input."""
        classifier = RandomForest(
            name="classifier_name",
            classes=["0", "1"],
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        # Create a list of AnnotatedEmbedding objects
        annotated_embeddings = [
            AnnotatedEmbedding(
                # 512-dimensional embedding
                embedding=[uniform(0.0, 1.0) for _ in range(512)],
                # Binary labels (0 or 1)
                annotation=str(randint(0, 1)),
            )
            for i in range(10)  # Generate 10 samples
        ]
        classifier.train(annotated_embeddings)
        # Check if the model is trained.
        validation.check_is_fitted(classifier._model)

    def test_predict(self) -> None:
        """Test the predict method with valid input."""
        classes = [
            "cat",
            "snake",
            "bird",
            "dog",
        ]
        classifier = RandomForest(
            name="classifier_name",
            classes=classes,
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        # Step 1: Define embeddings for training
        annotated_embeddings = [
            AnnotatedEmbedding(
                embedding=[0.1, 0.2],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.11, 0.12],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.12, 0.22],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.91, 0.92],
                annotation="dog",
            ),
            AnnotatedEmbedding(
                embedding=[1.0, 0.92],
                annotation="dog",
            ),
        ]

        classifier.train(annotated_embeddings)

        test_embeddings = [
            [0.15, 0.25],
            [0.99, 0.8],
        ]
        predictions = classifier.predict(test_embeddings)
        assert len(predictions) == len(test_embeddings)

        # Check predicion. First embedding should be "cat" and second "dog".
        assert np.allclose(predictions, [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]], atol=0.1)
        # Predict with empty input.
        predictions = classifier.predict([])
        assert len(predictions) == 0

    def test_predict__single_class(self) -> None:
        """Test the classify method with valid input."""
        classes = [
            "cat",
        ]
        classifier = RandomForest(
            name="classifier_name",
            classes=classes,
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        # Step 1: Define embeddings for training
        annotated_embeddings = [
            AnnotatedEmbedding(
                embedding=[0.1, 0.2],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.11, 0.12],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.12, 0.22],
                annotation="cat",
            ),
        ]

        classifier.train(annotated_embeddings)

        test_embeddings = [
            [0.15, 0.25],
            [0.99, 0.8],
        ]
        predictions = classifier.predict(test_embeddings)
        assert len(predictions) == len(test_embeddings)

        # Check predictions.
        assert np.allclose(predictions, [[1.0], [1.0]], atol=0.1)

    def test_train__no_training_data(self) -> None:
        """Test training with empty data."""
        classifier = RandomForest(
            name="classifier_name",
            classes=["1"],
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        with pytest.raises(
            ValueError,
            match="annotated_embeddings cannot be empty.",
        ):
            classifier.train([])

    def test_train__invalid_class(self) -> None:
        """Test the train method with invalid class."""
        classes = [
            "cat",
        ]
        classifier = RandomForest(
            name="classifier_name",
            classes=classes,
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        # Step 1: Define embeddings for training
        annotated_embeddings = [
            AnnotatedEmbedding(
                embedding=[0.1, 0.2],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.11, 0.12],
                annotation="dog",
            ),
        ]
        with pytest.raises(
            ValueError,
            match="Found labels not in predefined classes: {'dog'}",
        ):
            classifier.train(annotated_embeddings)

    def test_init__empty_class_list(self) -> None:
        """Test initialization with empty class list."""
        with pytest.raises(
            ValueError,
            match="Class list cannot be empty",
        ):
            RandomForest(
                name="classifier_name",
                classes=[],
                embedding_model_hash="hash",
                embedding_model_name="name",
            )

    def test_predict__different_input_class_order(self) -> None:
        """Test the order of the output prediction."""
        # Define embeddings for training
        annotated_embeddings = [
            AnnotatedEmbedding(
                embedding=[0.1, 0.2],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.11, 0.12],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.12, 0.22],
                annotation="cat",
            ),
            AnnotatedEmbedding(
                embedding=[0.91, 0.92],
                annotation="dog",
            ),
            AnnotatedEmbedding(
                embedding=[1.0, 0.92],
                annotation="dog",
            ),
        ]
        test_embeddings = [
            [0.15, 0.25],
            [0.99, 0.8],
        ]

        classes = ["cat", "snake", "bird", "dog"]
        classifier = RandomForest(
            name="classifier_name",
            classes=classes,
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        classifier.train(annotated_embeddings)
        predictions = classifier.predict(test_embeddings)

        # Check prediction.
        # The first embedding should be classified as "cat" (class index 0),
        # and the second as "dog" (class index 3).
        assert np.allclose(predictions, [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]], atol=0.1)

        # Change class order.
        classes = ["dog", "snake", "bird", "cat"]
        classifier = RandomForest(
            name="classifier_name",
            classes=classes,
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        classifier.train(annotated_embeddings)
        predictions = classifier.predict(test_embeddings)

        # Check prediction. Now imput class order is switched.
        # The first embedding should be classified as "cat" (class index 3),
        # and the second as "dog" (class index 0).
        assert np.allclose(predictions, [[0.0, 0.0, 0.0, 1.0], [1.0, 0.0, 0.0, 0.0]], atol=0.1)

    def test_load_classifier__sklearn_format(self, tmp_path: Path) -> None:
        """Test the export and load functionality."""
        classifier = RandomForest(
            name="classifier_name",
            classes=["0", "1"],
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        # Step 1: Define embeddings for training
        annotated_embeddings = [
            AnnotatedEmbedding(
                embedding=[
                    0.1,
                    0.2,
                    0.3,
                    0.4,
                    0.5,
                ],
                annotation="0",  # Class 0
            ),
            AnnotatedEmbedding(
                embedding=[1.0, 0.9, 0.8, 0.7, 0.6],
                annotation="1",  # Class 1
            ),
        ]

        classifier.train(annotated_embeddings)
        export_path = Path(tmp_path / "test_model_sklearn_instance.pkl")
        classifier.export(export_path, export_type="sklearn")

        loaded_classifier = load_random_forest_classifier(
            classifier_path=Path(tmp_path / "test_model_sklearn_instance.pkl"),
            buffer=None,
        )
        test_embeddings = [
            [0.15, 0.25, 0.35, 0.145, 0.155],
            [0.9, 0.8, 0.7, 0.6, 0.6],
        ]
        predictions = classifier.predict(test_embeddings)
        predictions_exported_model = loaded_classifier.predict(test_embeddings)
        # Check that the predictions from the 2 classifiers are the same.
        assert predictions == predictions_exported_model

    def test_export__lightly_format_root_is_leaf(self, tmp_path: Path) -> None:
        """Test the export raw functionality.

        The root becomes a leaf because the training set has only 2 samples.
        RandomForest uses bootstrapping, so some trees may see only one class
        and cannot split. In that case, the root node is a leaf that outputs
        a fixed class probability.
        """
        classifier = RandomForest(
            name="classifier_name",
            classes=["0", "2", "1"],
            embedding_model_hash="hash",
            embedding_model_name="name",
        )
        # Step 1: Define embeddings for training
        annotated_embeddings = [
            AnnotatedEmbedding(
                embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
                annotation="0",  # Class 0
            ),
            AnnotatedEmbedding(
                embedding=[1.0, 0.9, 0.8, 0.7, 0.6],
                annotation="1",  # Class 1
            ),
        ]

        classifier.train(annotated_embeddings)
        export_path = Path(tmp_path / "test_model_lightly.pkl")
        classifier.export(export_path, export_type="lightly")

        test_embeddings = [
            [0.15, 0.25, 0.35, 0.145, 0.155],
            [0.9, 0.8, 0.7, 0.6, 0.6],
        ]
        exported_classifier = load_lightly_random_forest(path=export_path, buffer=None)

        predictions = classifier.predict(test_embeddings)
        predictions_exported_model = predict_with_lightly_random_forest(
            exported_classifier, test_embeddings
        )
        assert np.allclose(predictions, predictions_exported_model, atol=1e-8)

    def test_export__lightly_format(self, tmp_path: Path) -> None:
        """Test the export raw functionality."""
        n_samples = 1000
        n_features = 128
        n_classes = 100

        class_labels = [f"class_{i}" for i in range(n_classes)]
        rng = np.random.default_rng(seed=42)

        annotated_embeddings = [
            AnnotatedEmbedding(
                embedding=rng.random(n_features).tolist(),
                annotation=str(rng.choice(class_labels)),
            )
            for _ in range(n_samples)
        ]
        # Add a class label to the beginning of the list to check that the
        # predictions are in the correct order, using all the classes not olny
        # the ones that are in the training data.
        class_labels.insert(0, "class_A")
        classifier = RandomForest(
            name="classifier_name",
            classes=class_labels,
            embedding_model_hash="hash",
            embedding_model_name="test_model",
        )
        classifier.train(annotated_embeddings)
        export_path = Path(tmp_path / "test_model_lightly.pkl")
        classifier.export(export_path, export_type="lightly")

        test_embeddings = [rng.random(n_features).tolist() for _ in range(1000)]
        exported_classifier = load_lightly_random_forest(path=export_path, buffer=None)

        predictions = classifier.predict(test_embeddings)
        predictions_exported_model = predict_with_lightly_random_forest(
            exported_classifier, test_embeddings
        )
        assert np.allclose(predictions, predictions_exported_model, atol=1e-6)

    def test_export__to_buffer(self) -> None:
        """Test exporting the classifier to a buffer."""
        classifier = RandomForest(
            name="classifier_name",
            classes=["0", "1"],
            embedding_model_hash="hash",
            embedding_model_name="name",
        )

        # Create training data
        annotated_embeddings = [
            AnnotatedEmbedding(
                embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
                annotation="0",
            ),
            AnnotatedEmbedding(
                embedding=[1.0, 0.9, 0.8, 0.7, 0.6],
                annotation="1",
            ),
        ]

        classifier.train(annotated_embeddings)
        test_embeddings = [
            [0.15, 0.25, 0.35, 0.145, 0.155],
            [0.9, 0.8, 0.7, 0.6, 0.6],
        ]

        # Test sklearn export format.
        buffer_sklearn = io.BytesIO()
        classifier.export(export_path=None, buffer=buffer_sklearn, export_type="sklearn")
        buffer_sklearn.seek(0)
        loaded_classifier_sklearn = load_random_forest_classifier(
            buffer=buffer_sklearn, classifier_path=None
        )
        predictions_sklearn = loaded_classifier_sklearn.predict(test_embeddings)

        # Test lightly export format.
        buffer_lightly = io.BytesIO()
        classifier.export(export_path=None, buffer=buffer_lightly, export_type="lightly")
        buffer_lightly.seek(0)
        loaded_classifier_lightly = load_lightly_random_forest(buffer=buffer_lightly, path=None)
        predictions_lightly = predict_with_lightly_random_forest(
            loaded_classifier_lightly, test_embeddings
        )

        # Original predictions for comparison.
        predictions_original = classifier.predict(test_embeddings)

        # Verify predictions match for both export formats.
        assert np.allclose(predictions_original, predictions_sklearn, atol=1e-6)
        assert np.allclose(predictions_original, predictions_lightly, atol=1e-6)
