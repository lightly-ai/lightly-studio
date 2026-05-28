"""Test sampling API endpoints."""

from __future__ import annotations

from collections import Counter

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.api.routes.api import sampling as sampling_api
from lightly_studio.metadata import compute_typicality
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    image_resolver,
    tag_resolver,
    video_resolver,
)
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.sampling.sampling_config import EmbeddingDiversityStrategy
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub
from tests.resolvers.video import helpers as video_helpers


def test_create_combination_sampling__diversity_success(
    test_client: TestClient, db_session: Session
) -> None:
    """Test successful diversity sampling."""
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=10, embedding_model_names=["test_embedding_model"]
    )

    request_data = {
        "n_samples_to_select": 3,
        "sampling_result_tag_name": "test_combination_sampling",
        "strategies": [
            {
                "strategy_name": "diversity",
                "embedding_model_name": "test_embedding_model",
            }
        ],
    }

    response = test_client.post(f"/api/collections/{collection_id}/sampling", json=request_data)

    # Assert 204 No Content response
    assert response.status_code == 204
    assert response.text == ""  # No response body

    # Verify tag was created with correct samples
    created_tag = tag_resolver.get_by_name(
        session=db_session, tag_name="test_combination_sampling", collection_id=collection_id
    )
    assert created_tag is not None

    # Verify correct number of samples were selected
    tag_filter = ImageFilter(sample_filter=SampleFilter(tag_ids=[created_tag.tag_id]))
    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, filters=tag_filter
    )
    assert len(result.samples) == 3


def test_create_sampling__passes_request_to_sampling(
    db_session: Session, mocker: MockerFixture
) -> None:
    """Test selection endpoint passes the request payload to sampling."""
    collection = helpers_resolvers.create_collection(
        session=db_session,
        collection_name="legacy-selection-test",
    )
    spy = mocker.patch.object(sampling_api, "sampling_via_database")
    mocker.patch.object(image_resolver, "get_sample_ids", return_value=["a", "b", "c"])

    sampling_api.create_sampling(
        session=db_session,
        collection=collection,
        request=sampling_api.SamplingRequest(
            n_samples_to_select=3,
            sampling_result_tag_name="selection_tag",
            strategies=[
                EmbeddingDiversityStrategy(
                    strategy_name="diversity",
                    embedding_model_name="test_embedding_model",
                )
            ],
        ),
    )

    config = spy.call_args.kwargs["config"]
    assert config.sampling_result_tag_name == "selection_tag"


def test_create_combination_sampling__diversity_success_videos(
    test_client: TestClient, db_session: Session
) -> None:
    """Test successful diversity sampling on a video collection."""
    collection_id = helpers_resolvers.fill_db_with_video_samples_and_embeddings(
        session=db_session, n_samples=10, embedding_model_names=["test_embedding_model"]
    )

    request_data = {
        "n_samples_to_select": 3,
        "sampling_result_tag_name": "test_combination_sampling",
        "strategies": [
            {
                "strategy_name": "diversity",
                "embedding_model_name": "test_embedding_model",
            }
        ],
    }

    response = test_client.post(f"/api/collections/{collection_id}/sampling", json=request_data)

    assert response.status_code == 204
    assert response.text == ""

    created_tag = tag_resolver.get_by_name(
        session=db_session, tag_name="test_combination_sampling", collection_id=collection_id
    )
    assert created_tag is not None

    tag_filter = VideoFilter(sample_filter=SampleFilter(tag_ids=[created_tag.tag_id]))
    result = video_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, filters=tag_filter
    )
    assert len(result.samples) == 3


def test_create_combination_sampling__insufficient_samples(
    test_client: TestClient, db_session: Session
) -> None:
    """Test diversity sampling when requesting more samples than available."""
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=2, embedding_model_names=["test_embedding_model"]
    )

    request_data = {
        "n_samples_to_select": 5,
        "sampling_result_tag_name": "test_sampling",
        "strategies": [
            {
                "strategy_name": "diversity",
                "embedding_model_name": "test_embedding_model",
            }
        ],
    }

    response = test_client.post(f"/api/collections/{collection_id}/sampling", json=request_data)

    assert response.status_code == 400
    assert "cannot select 5" in response.json()["detail"]
    assert "has only 2 samples" in response.json()["detail"]


def test_create_combination_sampling__duplicate_tag_name(
    test_client: TestClient, db_session: Session
) -> None:
    """Test diversity sampling when tag name already exists."""
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=5, embedding_model_names=["test_embedding_model"]
    )

    request_data = {
        "n_samples_to_select": 3,
        "sampling_result_tag_name": "duplicate_tag",
        "strategies": [
            {
                "strategy_name": "diversity",
                "embedding_model_name": "test_embedding_model",
            }
        ],
    }

    # First request should succeed
    response = test_client.post(f"/api/collections/{collection_id}/sampling", json=request_data)
    assert response.status_code == 204

    # Second request with same tag name should fail
    response = test_client.post(f"/api/collections/{collection_id}/sampling", json=request_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["error"]


def test_create_combination_sampling__metadata_weighting_success(
    test_client: TestClient, db_session: Session
) -> None:
    """Test successful diversity sampling."""
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
        "sampling_result_tag_name": "test_combination_sampling",
        "strategies": [
            {"strategy_name": "weights", "metadata_key": "typicality"},
            {
                "strategy_name": "diversity",
                "strength": 0.01,
                "embedding_model_name": "test_embedding_model",
            },
        ],
    }

    response = test_client.post(f"/api/collections/{collection_id}/sampling", json=request_data)

    # Assert 204 No Content response
    assert response.status_code == 204
    assert response.text == ""  # No response body

    # Verify tag was created with correct samples
    created_tag = tag_resolver.get_by_name(
        session=db_session, tag_name="test_combination_sampling", collection_id=collection_id
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


def test_create_combination_sampling__metadata_weighting_success_videos(
    test_client: TestClient, db_session: Session
) -> None:
    """Test successful metadata weighting + diversity sampling on a video collection."""
    collection = helpers_resolvers.create_collection(
        session=db_session,
        collection_name="test_video_collection",
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
        "sampling_result_tag_name": "test_combination_sampling",
        "strategies": [
            {"strategy_name": "weights", "metadata_key": "typicality"},
            {
                "strategy_name": "diversity",
                "strength": 0.01,
                "embedding_model_name": "test_embedding_model",
            },
        ],
    }

    response = test_client.post(f"/api/collections/{collection_id}/sampling", json=request_data)

    assert response.status_code == 204
    assert response.text == ""

    created_tag = tag_resolver.get_by_name(
        session=db_session, tag_name="test_combination_sampling", collection_id=collection_id
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


def test_create_combination_sampling__embedding_similarity_success(
    test_client: TestClient, db_session: Session
) -> None:
    """Similarity sampling creates a tag with the most similar samples."""
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
    )
    all_samples = image_resolver.get_all_by_collection_id(
        session=db_session, pagination=None, collection_id=collection_id
    ).samples
    query_tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=collection_id, tag_name="query_tag"
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=query_tag.tag_id,
        sample_ids=[all_samples[0].sample_id, all_samples[1].sample_id],
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 2,
            "sampling_result_tag_name": "similarity_sampling",
            "strategies": [
                {
                    "strategy_name": "similarity",
                    "query_tag_name": "query_tag",
                    "embedding_model_name": "embedding_model_1",
                }
            ],
        },
    )

    assert response.status_code == 204
    assert response.text == ""

    created_tag = tag_resolver.get_by_name(
        session=db_session,
        tag_name="similarity_sampling",
        collection_id=collection_id,
    )
    assert created_tag is not None

    tag_filter = ImageFilter(sample_filter=SampleFilter(tag_ids=[created_tag.tag_id]))
    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, filters=tag_filter
    )
    actual_sample_paths = {sample.file_path_abs for sample in result.samples}
    assert actual_sample_paths == {"sample_0.jpg", "sample_1.jpg"}


def test_create_combination_sampling__embedding_similarity_missing_query_tag(
    test_client: TestClient, db_session: Session
) -> None:
    """Similarity sampling fails if the query tag does not exist."""
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 2,
            "sampling_result_tag_name": "similarity_sampling",
            "strategies": [
                {
                    "strategy_name": "similarity",
                    "query_tag_name": "missing_query_tag",
                    "embedding_model_name": "embedding_model_1",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Query tag with name missing_query_tag not found."


def test_create_combination_sampling__embedding_similarity_query_tag_without_embeddings(
    test_client: TestClient, db_session: Session
) -> None:
    """Similarity sampling fails if the query tag has no embeddings."""
    collection_id = helpers_resolvers.fill_db_with_samples_and_embeddings(
        session=db_session, n_samples=5, embedding_model_names=["embedding_model_1"]
    )
    helpers_resolvers.create_tag(
        session=db_session, collection_id=collection_id, tag_name="empty_query_tag"
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 2,
            "sampling_result_tag_name": "similarity_sampling",
            "strategies": [
                {
                    "strategy_name": "similarity",
                    "query_tag_name": "empty_query_tag",
                    "embedding_model_name": "embedding_model_1",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == (
        "Query tag empty_query_tag does not have embeddings for embedding model embedding_model_1."
    )


def test_create_combination_sampling__annotation_class_balancing_success(
    test_client: TestClient, db_session: Session
) -> None:
    """Class balancing sampling returns an even class distribution."""
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="annotation_balancing_collection"
    )
    class_a = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="class_a",
    )
    class_b = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="class_b",
    )
    images = helpers_resolvers.create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="sample_a_1.jpg"),
            ImageStub(path="sample_a_2.jpg"),
            ImageStub(path="sample_b_1.jpg"),
            ImageStub(path="sample_b_2.jpg"),
        ],
    )
    helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=images[0].sample_id,
                annotation_label_id=class_a.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=images[1].sample_id,
                annotation_label_id=class_a.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=images[2].sample_id,
                annotation_label_id=class_b.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=images[3].sample_id,
                annotation_label_id=class_b.annotation_label_id,
            ),
        ],
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/sampling",
        json={
            "n_samples_to_select": 2,
            "sampling_result_tag_name": "balanced_sampling",
            "strategies": [
                {
                    "strategy_name": "balance",
                    "target_distribution": "uniform",
                }
            ],
        },
    )

    assert response.status_code == 204
    assert response.text == ""

    created_tag = tag_resolver.get_by_name(
        session=db_session,
        tag_name="balanced_sampling",
        collection_id=collection.collection_id,
    )
    assert created_tag is not None

    tag_filter = ImageFilter(sample_filter=SampleFilter(tag_ids=[created_tag.tag_id]))
    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id, filters=tag_filter
    )
    assert len(result.samples) == 2
    selected_annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session,
        parent_sample_ids=[sample.sample_id for sample in result.samples],
    )
    selected_label_names = annotation_label_resolver.names_by_ids(
        session=db_session,
        ids=[annotation.annotation_label_id for annotation in selected_annotations],
    )
    selected_class_frequencies = Counter(
        selected_label_names[str(annotation.annotation_label_id)]
        for annotation in selected_annotations
    )
    assert selected_class_frequencies == {"class_a": 1, "class_b": 1}


def test_create_combination_sampling__image_filter_success(
    test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Sampling succeeds when request fits within the ImageFilter pool."""
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="test_collection"
    )
    collection_id = collection.collection_id
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="test_embedding_model",
    )
    helpers_resolvers.create_samples_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (helpers_resolvers.ImageStub(path="narrow.jpg", width=100), [1.0, 0.0, 0.0]),
            (helpers_resolvers.ImageStub(path="wide1.jpg", width=300), [0.0, 1.0, 0.0]),
            (helpers_resolvers.ImageStub(path="wide2.jpg", width=300), [0.0, 0.0, 1.0]),
        ],
    )
    spy_sample_resolver = mocker.spy(image_resolver, "get_sample_ids")

    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 2,
            "sampling_result_tag_name": "tag1",
            "strategies": [
                {"strategy_name": "diversity", "embedding_model_name": "test_embedding_model"}
            ],
            "filter": {"filter_type": "image", "width": {"min": 200}},
        },
    )

    assert response.status_code == 204
    spy_sample_resolver.assert_called_once_with(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            width=FilterDimensions(min=200),
        ),
    )


def test_create_combination_sampling__video_filter_success(
    test_client: TestClient,
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Sampling succeeds when request fits within the VideoFilter pool."""
    collection = helpers_resolvers.create_collection(
        session=db_session,
        collection_name="test_video_collection",
        sample_type=SampleType.VIDEO,
    )
    collection_id = collection.collection_id
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="test_embedding_model",
    )
    narrow_video = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="narrow.mp4", width=100),
    )
    wide_video1 = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="wide1.mp4", width=300),
    )
    wide_video2 = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="wide2.mp4", width=300),
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=narrow_video.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 0.0, 0.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=wide_video1.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 1.0, 0.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=wide_video2.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 0.0, 1.0],
    )
    spy_video_resolver = mocker.spy(video_resolver, "get_sample_ids")

    response = test_client.post(
        f"/api/collections/{collection_id}/sampling",
        json={
            "n_samples_to_select": 2,
            "sampling_result_tag_name": "tag1",
            "strategies": [
                {"strategy_name": "diversity", "embedding_model_name": "test_embedding_model"}
            ],
            "filter": {"filter_type": "video", "width": {"min": 200}},
        },
    )

    assert response.status_code == 204
    spy_video_resolver.assert_called_once_with(
        session=db_session,
        collection_id=collection_id,
        filters=VideoFilter(
            width=FilterDimensions(min=200),
        ),
    )


def test_create_combination_sampling__image_collection_rejects_video_filter(
    test_client: TestClient, db_session: Session
) -> None:
    """Image collections reject video filters."""
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="test_collection"
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/sampling",
        json={
            "n_samples_to_select": 1,
            "sampling_result_tag_name": "tag1",
            "strategies": [
                {"strategy_name": "diversity", "embedding_model_name": "test_embedding_model"}
            ],
            "filter": {"filter_type": "video", "width": {"min": 200}},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid filter type for image collection."


def test_create_combination_sampling__video_collection_rejects_image_filter(
    test_client: TestClient, db_session: Session
) -> None:
    """Video collections reject image filters."""
    collection = helpers_resolvers.create_collection(
        session=db_session,
        collection_name="test_video_collection",
        sample_type=SampleType.VIDEO,
    )

    response = test_client.post(
        f"/api/collections/{collection.collection_id}/sampling",
        json={
            "n_samples_to_select": 1,
            "sampling_result_tag_name": "tag1",
            "strategies": [
                {"strategy_name": "diversity", "embedding_model_name": "test_embedding_model"}
            ],
            "filter": {"filter_type": "image", "width": {"min": 200}},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid filter type for video collection."
