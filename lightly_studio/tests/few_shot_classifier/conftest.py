"""Configuration of the tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio import few_shot_classifier
from lightly_studio.few_shot_classifier.classifier import AnnotatedEmbedding
from lightly_studio.few_shot_classifier.classifier_manager import (
    ClassifierEntry,
    ClassifierManager,
)
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.embedding_model import (
    EmbeddingModelCreate,
    EmbeddingModelTable,
)
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import embedding_model_resolver


@pytest.fixture
def fine_tuning_embeddings() -> list[SampleEmbeddingTable]:
    """Create test embeddings."""
    high_values = [
        SampleEmbeddingTable(sample_id=uuid4(), embedding=[0.95, 0.95, 0.95]) for _ in range(12)
    ]

    mid_values = [
        SampleEmbeddingTable(sample_id=uuid4(), embedding=[0.4, 0.4, 0.4]) for _ in range(10)
    ]

    low_values = [
        SampleEmbeddingTable(sample_id=uuid4(), embedding=[0.2, 0.2, 0.2]) for _ in range(10)
    ]

    return high_values + mid_values + low_values


@pytest.fixture
def embedding_model(db_session: Session, dataset: DatasetTable) -> EmbeddingModelTable:
    """Fixture to create an embedding model."""
    embedding_model = EmbeddingModelCreate(
        embedding_model_hash="mock_hash",
        name="test_model",
        dataset_id=dataset.dataset_id,
        embedding_dimension=3,
    )
    return embedding_model_resolver.create(session=db_session, embedding_model=embedding_model)


@pytest.fixture
def classifier_manager(
    classifier: ClassifierEntry,
) -> ClassifierManager:
    """Fixture to create a classifier manager."""
    classifier_manager = ClassifierManager()
    classifier_manager._classifiers[classifier.classifier_id] = classifier
    return classifier_manager


@pytest.fixture
def classifier(
    db_session: Session,
    dataset: DatasetTable,
    mocker: MockerFixture,
    embedding_model: EmbeddingModelTable,  # noqa: ARG001
) -> ClassifierEntry:
    """Fixture to create a few-shot classifier."""
    classifier_manager = ClassifierManager()

    mocker.patch.object(
        few_shot_classifier.classifier_manager,
        "_create_annotated_embeddings",
        return_value=[AnnotatedEmbedding(embedding=[0.1, 0.2, 0.3], annotation="class1")],
    )
    input_clases = ["class1"]
    # Create a classifier.
    classifier = classifier_manager.create_classifier(
        session=db_session,
        name="test_classifier",
        class_list=input_clases,
        dataset_id=dataset.dataset_id,
    )
    classifier_manager.update_classifiers_annotations(
        classifier_id=classifier.classifier_id,
        new_annotations={
            "class1": [uuid4(), uuid4()],
        },
    )
    classifier_manager.train_classifier(session=db_session, classifier_id=classifier.classifier_id)
    classifier_manager.commit_temp_classifier(classifier_id=classifier.classifier_id)
    return classifier
