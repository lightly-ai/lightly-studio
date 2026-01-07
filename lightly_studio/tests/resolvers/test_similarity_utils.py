from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers.similarity_utils import (
    distance_to_similarity,
    get_distance_expression,
)
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
)


class TestDistanceToSimilarity:
    """Tests for distance_to_similarity function."""

    def test_zero_distance(self) -> None:
        """Zero distance should return 1.0 similarity."""
        assert distance_to_similarity(0.0) == 1.0

    def test_max_distance(self) -> None:
        """Distance of 1.0 should return 0.0 similarity."""
        assert distance_to_similarity(1.0) == 0.0

    def test_half_distance(self) -> None:
        """Distance of 0.5 should return 0.5 similarity."""
        assert distance_to_similarity(0.5) == 0.5


class TestGetDistanceExpression:
    """Tests for get_distance_expression function."""

    def test_no_embedding__returns_none(self, test_db: Session) -> None:
        """When no text_embedding is provided, returns (None, None)."""
        collection = create_collection(session=test_db)

        embedding_model_id, distance_expr = get_distance_expression(
            session=test_db,
            collection_id=collection.collection_id,
            text_embedding=None,
        )

        assert embedding_model_id is None
        assert distance_expr is None

    def test_no_embedding_model__returns_none(self, test_db: Session) -> None:
        """When no embedding model exists for collection, returns (None, None)."""
        collection = create_collection(session=test_db)

        embedding_model_id, distance_expr = get_distance_expression(
            session=test_db,
            collection_id=collection.collection_id,
            text_embedding=[1.0, 0.0, 0.0],
        )

        assert embedding_model_id is None
        assert distance_expr is None

    def test_with_embedding_model__returns_expression(self, test_db: Session) -> None:
        """When embedding model exists, returns the model ID and distance expression."""
        collection = create_collection(session=test_db)
        embedding_model = create_embedding_model(
            session=test_db,
            collection_id=collection.collection_id,
            embedding_model_name="test_model",
            embedding_dimension=3,
        )

        embedding_model_id, distance_expr = get_distance_expression(
            session=test_db,
            collection_id=collection.collection_id,
            text_embedding=[1.0, 0.0, 0.0],
        )

        assert embedding_model_id == embedding_model.embedding_model_id
        assert distance_expr is not None
