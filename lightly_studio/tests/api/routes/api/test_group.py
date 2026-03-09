import uuid

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
                "sample_filter": {
                    "collection_id": str(group_col.collection_id),
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
                "sample_filter": {
                    "tag_ids": [str(other_tag.tag_id)],
                    "collection_id": str(group_col.collection_id),
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
    """Test that API returns group_preview for each group."""
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

    # Verify each group has group_preview populated
    for group_data in result["data"]:
        assert "group_preview" in group_data
        assert group_data["group_preview"] is not None
        assert group_data["group_preview"]["type"] == "image"
        assert "sample_id" in group_data["group_preview"]
        assert "file_name" in group_data["group_preview"]
        assert "file_path_abs" in group_data["group_preview"]

    # Verify the returned images match what we created
    returned_image_paths = {group["group_preview"]["file_path_abs"] for group in result["data"]}
    expected_image_paths = {img.file_path_abs for img in front_images}
    assert returned_image_paths == expected_image_paths

    # Verify sample_count is present and correct (each group has 1 sample)
    assert all("sample_count" in group for group in result["data"])
    assert all(group["sample_count"] == 1 for group in result["data"])


def test_get_all_groups__without_collection_id(test_client: TestClient) -> None:
    """Test GET all groups endpoint without collection_id returns 400 error."""
    # Act - Query without collection_id should return error
    response = test_client.post(
        "/api/groups",
        params={
            "offset": 0,
            "limit": 10,
        },
        json={"filter": {"sample_filter": {}}},
    )

    # Assert - should return 400 Bad Request
    assert response.status_code == 400
    assert response.json() == {
        "error": "Collection ID must be provided in filters to fetch groups."
    }


def test_get_all_groups__returns_first_sample_with_images_and_videos(
    test_client: TestClient, db_session: Session
) -> None:
    """Test that API returns group_preview (image preferred) for groups with mixed content.

    When a group contains both images and videos, the API returns:
    - group_preview: The first image sample (images are preferred over videos)
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

    # Verify each group has group_preview populated with image (image is preferred)
    for group_data in result["data"]:
        assert "group_preview" in group_data
        assert group_data["group_preview"] is not None
        assert group_data["group_preview"]["type"] == "image"
        assert "sample_id" in group_data["group_preview"]
        assert "file_name" in group_data["group_preview"]
        assert "file_path_abs" in group_data["group_preview"]

    # Verify the returned images match what we created
    returned_image_paths = {group["group_preview"]["file_path_abs"] for group in result["data"]}
    expected_image_paths = {img.file_path_abs for img in front_images}
    assert returned_image_paths == expected_image_paths

    # Verify sample_count is present and correct (each group has 2 samples: 1 image + 1 video)
    assert all("sample_count" in group for group in result["data"])
    assert all(group["sample_count"] == 2 for group in result["data"])


def test_get_group_components_by_group_id(test_client: TestClient, db_session: Session) -> None:
    """Test GET group components endpoint."""
    # Create group collection with multiple components
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create component samples
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]
    back_image = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path="back_0.jpg")],
    )[0]

    # Create a group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id, back_image.sample_id}],
    )[0]

    # Act
    response = test_client.get(f"/api/groups/{group_id}/components")

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert len(result) == 2

    # Verify component names
    component_names = {comp["collection"]["group_component_name"] for comp in result}
    assert component_names == {"front", "back"}

    # Verify component details by name
    components_by_name = {comp["collection"]["group_component_name"]: comp for comp in result}

    assert components_by_name["front"]["details"]["sample_id"] == str(front_image.sample_id)
    assert components_by_name["front"]["details"]["file_name"] == "front_0.jpg"
    assert components_by_name["front"]["details"]["type"] == "image"

    assert components_by_name["back"]["details"]["sample_id"] == str(back_image.sample_id)
    assert components_by_name["back"]["details"]["file_name"] == "back_0.jpg"
    assert components_by_name["back"]["details"]["type"] == "image"


def test_get_group_components_by_group_id__with_videos(
    test_client: TestClient, db_session: Session
) -> None:
    """Test GET group components endpoint with video components."""
    # Create group collection with image and video components
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("camera", SampleType.VIDEO)],
    )

    # Create component samples
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]
    video_ids = create_videos(
        session=db_session,
        collection_id=components["camera"].collection_id,
        videos=[VideoStub(path="camera_0.mp4")],
    )

    # Create a group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id, video_ids[0]}],
    )[0]

    # Act
    response = test_client.get(f"/api/groups/{group_id}/components")

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert len(result) == 2

    # Verify component names
    component_names = {comp["collection"]["group_component_name"] for comp in result}
    assert component_names == {"front", "camera"}

    # Verify component details by name
    components_by_name = {comp["collection"]["group_component_name"]: comp for comp in result}

    assert components_by_name["front"]["details"]["sample_id"] == str(front_image.sample_id)
    assert components_by_name["front"]["details"]["type"] == "image"

    assert components_by_name["camera"]["details"]["sample_id"] == str(video_ids[0])
    assert components_by_name["camera"]["details"]["file_name"] == "camera_0.mp4"
    assert components_by_name["camera"]["details"]["type"] == "video"


def test_get_group_components_by_group_id__partial_group(
    test_client: TestClient, db_session: Session
) -> None:
    """Test GET group components endpoint with partial group (not all components present)."""
    # Create group collection with multiple components
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create only front component sample
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]

    # Create a partial group (only has front component)
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id}],
    )[0]

    # Act
    response = test_client.get(f"/api/groups/{group_id}/components")

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert len(result) == 1

    component = result[0]
    assert component["collection"]["group_component_name"] == "front"
    assert component["details"]["sample_id"] == str(front_image.sample_id)
    assert component["details"]["type"] == "image"


def test_get_group_components_by_group_id__nonexistent_group(
    test_client: TestClient,
) -> None:
    """Test GET group components endpoint with non-existent group ID."""
    # Act
    non_existent_id = uuid.uuid4()
    response = test_client.get(f"/api/groups/{non_existent_id}/components")

    # Assert - should return empty list for non-existent group
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert result == []


def test_get_group_components_by_group_id__multiple_groups(
    test_client: TestClient, db_session: Session
) -> None:
    """Test GET group components endpoint returns only components for specified group."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create samples for two groups
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg"), ImageStub(path="front_1.jpg")],
    )
    back_images = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path="back_0.jpg"), ImageStub(path="back_1.jpg")],
    )

    # Create two groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[
            {front_images[0].sample_id, back_images[0].sample_id},
            {front_images[1].sample_id, back_images[1].sample_id},
        ],
    )

    # Act - Request components for first group
    response = test_client.get(f"/api/groups/{group_ids[0]}/components")

    # Assert
    assert response.status_code == HTTP_STATUS_OK
    result = response.json()
    assert len(result) == 2

    # Verify we got components from the first group only
    sample_ids = {comp["details"]["sample_id"] for comp in result}

    # Should contain samples from first group
    assert str(front_images[0].sample_id) in sample_ids
    assert str(back_images[0].sample_id) in sample_ids

    # Should NOT contain samples from second group
    assert str(front_images[1].sample_id) not in sample_ids
    assert str(back_images[1].sample_id) not in sample_ids
