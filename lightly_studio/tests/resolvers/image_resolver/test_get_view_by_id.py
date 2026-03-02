"""Tests for get_view resolver."""

from sqlmodel import Session

from lightly_studio.models.image import ImageView
from lightly_studio.resolvers import image_resolver, metadata_resolver, tag_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_caption,
    create_collection,
    create_image,
    create_tag,
)


def test_get_view_basic(db_session: Session) -> None:
    """Test getting view for an image."""
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/image.png",
    )

    result = image_resolver.get_view_by_id(session=db_session, sample_id=image.sample_id)

    assert isinstance(result, ImageView)
    assert result.sample_id == image.sample_id
    assert result.file_name == image.file_name
    assert result.file_path_abs == image.file_path_abs
    assert result.width == image.width
    assert result.height == image.height
    assert result.sample.sample_id == image.sample_id


def test_get_view_with_annotations(db_session: Session) -> None:
    """Test getting view for an image with annotations."""
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
    )

    # Add annotation
    label = create_annotation_label(
        session=db_session,
        dataset_id=collection.collection_id,
        label_name="test_label",
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    db_session.refresh(image)

    result = image_resolver.get_view_by_id(session=db_session, sample_id=image.sample_id)

    assert len(result.annotations) == 1
    assert result.annotations[0].annotation_label.annotation_label_name == "test_label"


def test_get_view_with_tags(db_session: Session) -> None:
    """Test getting view for an image with tags."""
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
    )

    # Add tag
    tag = create_tag(
        session=db_session,
        collection_id=collection.collection_id,
        tag_name="test_tag",
    )
    tag_resolver.add_tag_to_sample(
        session=db_session,
        tag_id=tag.tag_id,
        sample=image.sample,
    )
    db_session.refresh(image)

    result = image_resolver.get_view_by_id(session=db_session, sample_id=image.sample_id)

    assert len(result.tags) == 1
    assert result.tags[0].name == "test_tag"
    assert result.tags[0].tag_id == tag.tag_id


def test_get_view_with_metadata(db_session: Session) -> None:
    """Test getting view for an image with metadata."""
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
    )

    # Add metadata
    metadata_resolver.set_value_for_sample(
        session=db_session,
        sample_id=image.sample_id,
        key="test_key",
        value="test_value",
    )
    db_session.refresh(image)

    result = image_resolver.get_view_by_id(session=db_session, sample_id=image.sample_id)

    assert result.metadata_dict is not None
    assert result.metadata_dict.data["test_key"] == "test_value"


def test_get_view_with_captions(db_session: Session) -> None:
    """Test getting view for an image with captions."""
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
    )

    # Add caption
    create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=image.sample_id,
        text="test caption",
    )
    db_session.refresh(image)

    result = image_resolver.get_view_by_id(session=db_session, sample_id=image.sample_id)

    assert len(result.captions) == 1
    assert result.captions[0].text == "test caption"


def test_get_view_empty_collections(db_session: Session) -> None:
    """Test getting view for an image with no annotations, tags, captions, or metadata."""
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
    )

    result = image_resolver.get_view_by_id(session=db_session, sample_id=image.sample_id)

    assert len(result.annotations) == 0
    assert len(result.tags) == 0
    assert len(result.captions) == 0
    assert result.metadata_dict is None
