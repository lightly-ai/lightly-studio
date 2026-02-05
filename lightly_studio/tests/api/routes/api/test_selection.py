"""Test selection API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.metadata import compute_typicality
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import image_resolver, tag_resolver, video_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub
from tests.resolvers.video import helpers as video_helpers


class TestDiversitySelection:
    """Test class for diversity selection API endpoint."""

    def test_create_combination_selection__diversity_success(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test successful diversity selection."""
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
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

        response = test_client.post(
            f"/api/collections/{collection_id}/selection", json=request_data
        )

        # Assert 204 No Content response
        assert response.status_code == 204
        assert response.text == ""  # No response body

        # Verify tag was created with correct samples
        created_tag = tag_resolver.get_by_name(
            session=db_session, tag_name="test_combination_selection", collection_id=collection_id
        )
        assert created_tag is not None

        # Verify correct number of samples were selected
        tag_filter = ImageFilter(sample_filter=SampleFilter(tag_ids=[created_tag.tag_id]))
        result = image_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection_id, filters=tag_filter
        )
        assert len(result.samples) == 3

    def test_create_combination_selection__diversity_success_videos(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test successful diversity selection on a video collection."""
        collection_id = helpers_resolvers.fill_db_with_video_samples_and_embeddings(
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

        response = test_client.post(
            f"/api/collections/{collection_id}/selection", json=request_data
        )

        assert response.status_code == 204
        assert response.text == ""

        created_tag = tag_resolver.get_by_name(
            session=db_session, tag_name="test_combination_selection", collection_id=collection_id
        )
        assert created_tag is not None

        tag_filter = VideoFilter(sample_filter=SampleFilter(tag_ids=[created_tag.tag_id]))
        result = video_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection_id, filters=tag_filter
        )
        assert len(result.samples) == 3

    def test_create_combination_selection__insufficient_samples(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test diversity selection when requesting more samples than available."""
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
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

        response = test_client.post(
            f"/api/collections/{collection_id}/selection", json=request_data
        )

        assert response.status_code == 400
        assert "cannot select 5" in response.json()["detail"]
        assert "has only 2 samples" in response.json()["detail"]

    def test_create_combination_selection__duplicate_tag_name(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test diversity selection when tag name already exists."""
        collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
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
        response = test_client.post(
            f"/api/collections/{collection_id}/selection", json=request_data
        )
        assert response.status_code == 204

        # Second request with same tag name should fail
        response = test_client.post(
            f"/api/collections/{collection_id}/selection", json=request_data
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["error"]

    def test_create_combination_selection__metadata_weighting_success(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test successful diversity selection."""
        collection = helpers_resolvers.create_collection(
            session=db_session, collection_name="test_collection"
        )
        collection_id = collection.collection_id
        embedding_model = helpers_resolvers.create_embedding_model(
            session=db_session,
            collection_id=collection_id,
            embedding_model_name="test_embedding_model",
        )

        samples_with_embeddings = [
            (ImageStub(path="image1.jpg"), [1.0, 0.0, 0.0]),
            (ImageStub(path="image2.jpg"), [0.0, 1.0, 0.0]),
            (ImageStub(path="image3.jpg"), [0.0, 1.0, 1.0]),
        ]
        helpers_resolvers.create_samples_with_embeddings(
            session=db_session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            images_and_embeddings=samples_with_embeddings,
        )
        compute_typicality.compute_typicality_metadata(
            session=db_session,
            collection_id=collection_id,
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

        response = test_client.post(
            f"/api/collections/{collection_id}/selection", json=request_data
        )

        # Assert 204 No Content response
        assert response.status_code == 204
        assert response.text == ""  # No response body

        # Verify tag was created with correct samples
        created_tag = tag_resolver.get_by_name(
            session=db_session, tag_name="test_combination_selection", collection_id=collection_id
        )
        assert created_tag is not None

        # Verify correct number of samples were selected
        tag_filter = ImageFilter(sample_filter=SampleFilter(tag_ids=[created_tag.tag_id]))
        result = image_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection_id, filters=tag_filter
        )
        assert len(result.samples) == 2
        # 2nd embedding is the most typical, then the 3rd. 1st is farthest from them all.
        # Note that we also use diversity, but its strength is downgraded to 0.01.
        assert result.samples[0].file_name == "image2.jpg"
        assert result.samples[1].file_name == "image3.jpg"

    def test_create_combination_selection__metadata_weighting_success_videos(
        self, test_client: TestClient, db_session: Session
    ) -> None:
        """Test successful metadata weighting + diversity selection on a video collection."""
        collection = helpers_resolvers.create_collection(
            session=db_session,
            collection_name="test_collection",
            sample_type=SampleType.VIDEO,
        )
        collection_id = collection.collection_id
        embedding_model = helpers_resolvers.create_embedding_model(
            session=db_session,
            collection_id=collection_id,
            embedding_model_name="test_embedding_model",
        )

        videos_with_embeddings = [
            (video_helpers.VideoStub(path="video1.mp4"), [1.0, 0.0, 0.0]),
            (video_helpers.VideoStub(path="video2.mp4"), [0.0, 1.0, 0.0]),
            (video_helpers.VideoStub(path="video3.mp4"), [0.0, 1.0, 1.0]),
        ]
        for video_stub, embedding in videos_with_embeddings:
            video = video_helpers.create_video(
                session=db_session,
                collection_id=collection_id,
                video=video_stub,
            )
            helpers_resolvers.create_sample_embedding(
                session=db_session,
                sample_id=video.sample_id,
                embedding_model_id=embedding_model.embedding_model_id,
                embedding=embedding,
            )
        compute_typicality.compute_typicality_metadata(
            session=db_session,
            collection_id=collection_id,
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

        response = test_client.post(
            f"/api/collections/{collection_id}/selection", json=request_data
        )

        assert response.status_code == 204
        assert response.text == ""

        created_tag = tag_resolver.get_by_name(
            session=db_session, tag_name="test_combination_selection", collection_id=collection_id
        )
        assert created_tag is not None

        tag_filter = VideoFilter(sample_filter=SampleFilter(tag_ids=[created_tag.tag_id]))
        result = video_resolver.get_all_by_collection_id(
            session=db_session, collection_id=collection_id, filters=tag_filter
        )
        assert len(result.samples) == 2
        # Same logic as image test: 2nd and 3rd embeddings are most typical.
        assert result.samples[0].file_name == "video2.mp4"
        assert result.samples[1].file_name == "video3.mp4"
