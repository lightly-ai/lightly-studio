from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_OK
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver, tag_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images, create_tag
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_get_all_groups(test_client: TestClient, db_session: Session) -> None:
    """Test basic GET all groups endpoint."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[
            ImageStub(path="front_0.jpg"),
            ImageStub(path="front_1.jpg"),
        ],
    )

    # Create groups
    group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_images[0].sample_id}, {front_images[1].sample_id}],
    )

    # Act
    response = test_client.post(
        "/api/groups",
        params={
            "offset": 0,
            "limit": 10,
        },
        json={
            "filter": {
                "sample_filter": {
                    "collection_id": str(group_col.collection_id),
                }
            }
        },
    )

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()

    data = result["data"]
    assert result["total_count"] == 2
    assert len(data) == 2
    assert "sample_id" in data[0]
    assert "sample" in data[0]
    assert "sample_count" in data[0]
    # Each group has 1 sample
    assert all(group["sample_count"] == 1 for group in data)


def test_get_all_groups__with_pagination(test_client: TestClient, db_session: Session) -> None:
    """Test pagination in GET all groups endpoint."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(5)],
    )

    # Create groups
    group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    # Act - Get first page
    response = test_client.post(
        "/api/groups",
        params={
            "cursor": 0,
            "limit": 2,
        },
        json={
            "filter": {
                "sample_filter": {
                    "collection_id": str(group_col.collection_id),
                }
            }
        },
    )

    # Assert first page
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 5
    assert len(result["data"]) == 2
    assert result["nextCursor"] == 2

    # Act - Get second page
    response = test_client.post(
        "/api/groups",
        params={
            "cursor": 2,
            "limit": 2,
        },
        json={
            "filter": {
                "sample_filter": {
                    "collection_id": str(group_col.collection_id),
                }
            }
        },
    )

    # Assert second page
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 5
    assert len(result["data"]) == 2
    assert result["nextCursor"] == 4


def test_get_all_groups__with_tag_filter(test_client: TestClient, db_session: Session) -> None:
    """Test filtering in GET all groups endpoint."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(3)],
    )

    # Create groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    # Create tag and add first group to it
    tag = create_tag(session=db_session, collection_id=group_col.collection_id, tag_name="test_tag")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag.tag_id,
        sample_ids=[group_ids[0]],
    )

    # Act - Filter by tag_ids
    response = test_client.post(
        "/api/groups",
        params={
            "offset": 0,
            "limit": 10,
        },
        json={
            "filter": {
                "collection_id": str(group_col.collection_id),
                "sample_filter": {
                    "tag_ids": [str(tag.tag_id)],
                },
            }
        },
    )

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 1
    assert len(result["data"]) == 1
    assert result["data"][0]["sample_id"] == str(group_ids[0])

    # Act - Filter by a different tag with no groups assigned
    other_tag = create_tag(
        session=db_session, collection_id=group_col.collection_id, tag_name="other_tag"
    )
    response = test_client.post(
        "/api/groups",
        params={
            "offset": 0,
            "limit": 10,
        },
        json={
            "filter": {
                "collection_id": str(group_col.collection_id),
                "sample_filter": {
                    "tag_ids": [str(other_tag.tag_id)],
                },
            }
        },
    )

    # Assert - should return empty
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 0
    assert len(result["data"]) == 0


def test_get_all_groups__empty_collection(test_client: TestClient, db_session: Session) -> None:
    """Test GET all groups endpoint with empty collection."""
    # Create empty group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)

    # Act
    response = test_client.post(
        "/api/groups",
        params={
            "offset": 0,
            "limit": 10,
        },
        json={
            "filter": {
                "sample_filter": {
                    "collection_id": str(group_col.collection_id),
                }
            }
        },
    )

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 0
    assert len(result["data"]) == 0


def test_get_all_groups__returns_first_sample_image(
    test_client: TestClient, db_session: Session
) -> None:
    """Test that API returns group_snapshot for each group."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[
            ImageStub(path="front_0.jpg"),
            ImageStub(path="front_1.jpg"),
        ],
    )

    # Create groups
    group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_images[0].sample_id}, {front_images[1].sample_id}],
    )

    # Act
    response = test_client.post(
        "/api/groups",
        params={
            "offset": 0,
            "limit": 10,
        },
        json={
            "filter": {
                "sample_filter": {
                    "collection_id": str(group_col.collection_id),
                }
            }
        },
    )

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 2
    assert len(result["data"]) == 2

    # Verify each group has group_snapshot populated
    for group_data in result["data"]:
        assert "group_snapshot" in group_data
        assert group_data["group_snapshot"] is not None
        assert group_data["group_snapshot"]["type"] == "image"
        assert "sample_id" in group_data["group_snapshot"]
        assert "file_name" in group_data["group_snapshot"]
        assert "file_path_abs" in group_data["group_snapshot"]

    # Verify the returned images match what we created
    returned_image_paths = {group["group_snapshot"]["file_path_abs"] for group in result["data"]}
    expected_image_paths = {img.file_path_abs for img in front_images}
    assert returned_image_paths == expected_image_paths

    # Verify sample_count is present and correct (each group has 1 sample)
    assert all("sample_count" in group for group in result["data"])
    assert all(group["sample_count"] == 1 for group in result["data"])


def test_get_all_groups__returns_first_sample_with_images_and_videos(
    test_client: TestClient, db_session: Session
) -> None:
    """Test that API returns group_snapshot (image preferred) for groups with mixed content.

    When a group contains both images and videos, the API returns:
    - group_snapshot: The first image sample (images are preferred over videos)
    """
    # Create group collection with both image and video components
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[
            ("front", SampleType.IMAGE),
            ("video", SampleType.VIDEO),
        ],
    )

    # Create image samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[
            ImageStub(path="front_0.jpg"),
            ImageStub(path="front_1.jpg"),
        ],
    )

    # Create video samples
    video_ids = create_videos(
        session=db_session,
        collection_id=components["video"].collection_id,
        videos=[
            VideoStub(path="video_0.mp4"),
            VideoStub(path="video_1.mp4"),
        ],
    )

    # Create groups with both images and videos
    group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[
            {front_images[0].sample_id, video_ids[0]},
            {front_images[1].sample_id, video_ids[1]},
        ],
    )

    # Act
    response = test_client.post(
        "/api/groups",
        params={
            "offset": 0,
            "limit": 10,
        },
        json={
            "filter": {
                "sample_filter": {
                    "collection_id": str(group_col.collection_id),
                }
            }
        },
    )

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result["total_count"] == 2
    assert len(result["data"]) == 2

    # Verify each group has group_snapshot populated with image (image is preferred)
    for group_data in result["data"]:
        assert "group_snapshot" in group_data
        assert group_data["group_snapshot"] is not None
        assert group_data["group_snapshot"]["type"] == "image"
        assert "sample_id" in group_data["group_snapshot"]
        assert "file_name" in group_data["group_snapshot"]
        assert "file_path_abs" in group_data["group_snapshot"]

    # Verify the returned images match what we created
    returned_image_paths = {group["group_snapshot"]["file_path_abs"] for group in result["data"]}
    expected_image_paths = {img.file_path_abs for img in front_images}
    assert returned_image_paths == expected_image_paths

    # Verify sample_count is present and correct (each group has 2 samples: 1 image + 1 video)
    assert all("sample_count" in group for group in result["data"])
    assert all(group["sample_count"] == 2 for group in result["data"])
