"""Test selection API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.metadata import compute_typicality
from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.samples_filter import SampleFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub


class TestDiversitySelection:
    """Test class for diversity selection API endpoint."""

    def test_create_combination_selection__diversity_success(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test successful diversity selection."""
        dataset_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            test_db=db_session, n_samples=10, embedding_model_names=["test_embedding_model"]
        )

        request_data = {
            "n_samples_to_select": 3,
            "selection_result_tag_name": "test_combination_selection",
            "strategies": [
                {
                    "strategy_name": "diversity",
                    "embedding_model_name": "test_embedding_model",
                }
            ],
        }

        response = test_client.post(f"/api/datasets/{dataset_id}/selection", json=request_data)

        # Assert 204 No Content response
        assert response.status_code == 204
        assert response.text == ""  # No response body

        # Verify tag was created with correct samples
        created_tag = tag_resolver.get_by_name(
            session=db_session, tag_name="test_combination_selection", dataset_id=dataset_id
        )
        assert created_tag is not None

        # Verify correct number of samples were selected
        tag_filter = SampleFilter(tag_ids=[created_tag.tag_id])
        result = image_resolver.get_all_by_dataset_id(
            session=db_session, dataset_id=dataset_id, filters=tag_filter
        )
        assert len(result.samples) == 3

    def test_create_combination_selection__insufficient_samples(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test diversity selection when requesting more samples than available."""
        dataset_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            test_db=db_session, n_samples=2, embedding_model_names=["test_embedding_model"]
        )

        request_data = {
            "n_samples_to_select": 5,
            "selection_result_tag_name": "test_selection",
            "strategies": [
                {
                    "strategy_name": "diversity",
                    "embedding_model_name": "test_embedding_model",
                }
            ],
        }

        response = test_client.post(f"/api/datasets/{dataset_id}/selection", json=request_data)

        assert response.status_code == 400
        assert "cannot select 5" in response.json()["detail"]
        assert "has only 2 samples" in response.json()["detail"]

    def test_create_combination_selection__duplicate_tag_name(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test diversity selection when tag name already exists."""
        dataset_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
            test_db=db_session, n_samples=5, embedding_model_names=["test_embedding_model"]
        )

        request_data = {
            "n_samples_to_select": 3,
            "selection_result_tag_name": "duplicate_tag",
            "strategies": [
                {
                    "strategy_name": "diversity",
                    "embedding_model_name": "test_embedding_model",
                }
            ],
        }

        # First request should succeed
        response = test_client.post(f"/api/datasets/{dataset_id}/selection", json=request_data)
        assert response.status_code == 204

        # Second request with same tag name should fail
        response = test_client.post(f"/api/datasets/{dataset_id}/selection", json=request_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["error"]

    def test_create_combination_selection__metadata_weighting_success(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test successful diversity selection."""
        dataset = helpers_resolvers.create_dataset(session=db_session, dataset_name="test_dataset")
        dataset_id = dataset.dataset_id
        embedding_model = helpers_resolvers.create_embedding_model(
            session=db_session,
            dataset_id=dataset_id,
            embedding_model_name="test_embedding_model",
        )

        samples_with_embeddings = [
            (ImageStub(path="image1.jpg"), [1.0, 0.0, 0.0]),
            (ImageStub(path="image2.jpg"), [0.0, 1.0, 0.0]),
            (ImageStub(path="image3.jpg"), [0.0, 1.0, 1.0]),
        ]
        helpers_resolvers.create_samples_with_embeddings(
            db_session=db_session,
            dataset_id=dataset_id,
            embedding_model_id=embedding_model.embedding_model_id,
            images_and_embeddings=samples_with_embeddings,
        )
        compute_typicality.compute_typicality_metadata(
            session=db_session,
            dataset_id=dataset_id,
            embedding_model_id=embedding_model.embedding_model_id,
            metadata_name="typicality",
        )

        request_data = {
            "n_samples_to_select": 2,
            "selection_result_tag_name": "test_combination_selection",
            "strategies": [
                {"strategy_name": "weights", "metadata_key": "typicality"},
                {
                    "strategy_name": "diversity",
                    "strength": 0.01,
                    "embedding_model_name": "test_embedding_model",
                },
            ],
        }

        response = test_client.post(f"/api/datasets/{dataset_id}/selection", json=request_data)

        # Assert 204 No Content response
        assert response.status_code == 204
        assert response.text == ""  # No response body

        # Verify tag was created with correct samples
        created_tag = tag_resolver.get_by_name(
            session=db_session, tag_name="test_combination_selection", dataset_id=dataset_id
        )
        assert created_tag is not None

        # Verify correct number of samples were selected
        tag_filter = SampleFilter(tag_ids=[created_tag.tag_id])
        result = image_resolver.get_all_by_dataset_id(
            session=db_session, dataset_id=dataset_id, filters=tag_filter
        )
        assert len(result.samples) == 2
        # 2nd embedding is the most typical, then the 3rd. 1st is farthest from them all.
        # Note that we also use diversity, but its strength is downgraded to 0.01.
        assert result.samples[0].file_name == "image2.jpg"
        assert result.samples[1].file_name == "image3.jpg"
