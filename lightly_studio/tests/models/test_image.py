"""Tests for the Image model."""

from sqlmodel import Session

from lightly_studio.models.image import ImageView
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_caption,
    create_collection,
    create_image,
    create_tag,
)


class TestImageView:
    """Tests for the ImageView model."""

    def test_from_image_table__basic(self, db_session: Session) -> None:
        """Test basic conversion from ImageTable to ImageView."""
        # Create a collection and an image.
        collection = create_collection(session=db_session)
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs="/path/to/test_image.jpg",
            width=1920,
            height=1080,
        )

        # Convert to ImageView.
        image_view = ImageView.from_image_table(image=image)

        # Verify basic fields.
        assert image_view.file_name == "test_image.jpg"
        assert image_view.file_path_abs == "/path/to/test_image.jpg"
        assert image_view.sample_id == image.sample_id
        assert image_view.width == 1920
        assert image_view.height == 1080
        assert image_view.annotations == []
        assert image_view.captions == []
        assert image_view.tags == []
        assert image_view.metadata_dict is None

    def test_from_image_table__with_annotations(self, db_session: Session) -> None:
        """Test conversion with annotations."""
        # Create a collection, image, and annotation.
        collection = create_collection(session=db_session)
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
        )
        annotation_label = create_annotation_label(
            session=db_session,
            dataset_id=collection.collection_id,
            label_name="cat",
        )
        annotation = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=annotation_label.annotation_label_id,
        )

        # Refresh to get the annotations relationship loaded.
        db_session.refresh(image)

        # Convert to ImageView.
        image_view = ImageView.from_image_table(image=image)

        # Verify annotations are included.
        assert len(image_view.annotations) == 1
        assert image_view.annotations[0].sample_id == annotation.sample_id
        assert image_view.annotations[0].annotation_label.annotation_label_name == "cat"

    def test_from_image_table__with_captions(self, db_session: Session) -> None:
        """Test conversion with captions."""
        # Create a collection, image, and caption.
        collection = create_collection(session=db_session)
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
        )
        caption = create_caption(
            session=db_session,
            collection_id=collection.collection_id,
            parent_sample_id=image.sample_id,
            text="A beautiful sunset",
        )

        # Refresh to get the captions relationship loaded.
        db_session.refresh(image)

        # Convert to ImageView.
        image_view = ImageView.from_image_table(image=image)

        # Verify captions are included.
        assert len(image_view.captions) == 1
        assert image_view.captions[0].sample_id == caption.sample_id
        assert image_view.captions[0].text == "A beautiful sunset"

    def test_from_image_table__with_tags(self, db_session: Session) -> None:
        """Test conversion with tags."""
        # Create a collection, image, and tag.
        collection = create_collection(session=db_session)
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
        )
        tag = create_tag(
            session=db_session,
            collection_id=collection.collection_id,
            tag_name="outdoor",
        )

        # Add tag to the sample.
        image.sample.tags.append(tag)
        db_session.commit()
        db_session.refresh(image)

        # Convert to ImageView.
        image_view = ImageView.from_image_table(image=image)

        # Verify tags are included.
        assert len(image_view.tags) == 1
        assert image_view.tags[0].tag_id == tag.tag_id
        assert image_view.tags[0].name == "outdoor"
        assert image_view.tags[0].kind == "sample"

    def test_from_image_table__with_all_relationships(self, db_session: Session) -> None:
        """Test conversion with all relationships populated."""
        # Create a collection and image.
        collection = create_collection(session=db_session)
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs="/path/to/complex_image.jpg",
            width=800,
            height=600,
        )

        # Add annotation.
        annotation_label = create_annotation_label(
            session=db_session,
            dataset_id=collection.collection_id,
            label_name="dog",
        )
        annotation = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=annotation_label.annotation_label_id,
        )

        # Add caption.
        caption = create_caption(
            session=db_session,
            collection_id=collection.collection_id,
            parent_sample_id=image.sample_id,
            text="A dog playing in the park",
        )

        # Add tag.
        tag = create_tag(
            session=db_session,
            collection_id=collection.collection_id,
            tag_name="favorite",
        )
        image.sample.tags.append(tag)
        db_session.commit()

        # Refresh to get all relationships loaded.
        db_session.refresh(image)

        # Convert to ImageView.
        image_view = ImageView.from_image_table(image=image)

        # Verify all fields.
        assert image_view.file_name == "complex_image.jpg"
        assert image_view.file_path_abs == "/path/to/complex_image.jpg"
        assert image_view.width == 800
        assert image_view.height == 600
        assert len(image_view.annotations) == 1
        assert image_view.annotations[0].sample_id == annotation.sample_id
        assert len(image_view.captions) == 1
        assert image_view.captions[0].sample_id == caption.sample_id
        assert len(image_view.tags) == 1
        assert image_view.tags[0].tag_id == tag.tag_id
        assert image_view.sample.sample_id == image.sample_id
        assert image_view.sample.collection_id == collection.collection_id

    def test_from_image_table__with_multiple_annotations_and_captions(
        self, db_session: Session
    ) -> None:
        """Test conversion with multiple annotations and captions."""
        # Create a collection and image.
        collection = create_collection(session=db_session)
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
        )

        # Add multiple annotations.
        label1 = create_annotation_label(
            session=db_session,
            dataset_id=collection.collection_id,
            label_name="person",
        )
        label2 = create_annotation_label(
            session=db_session,
            dataset_id=collection.collection_id,
            label_name="car",
        )
        annotation1 = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label1.annotation_label_id,
        )
        annotation2 = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label2.annotation_label_id,
        )

        # Add multiple captions.
        create_caption(
            session=db_session,
            collection_id=collection.collection_id,
            parent_sample_id=image.sample_id,
            text="First caption",
        )
        create_caption(
            session=db_session,
            collection_id=collection.collection_id,
            parent_sample_id=image.sample_id,
            text="Second caption",
        )

        # Refresh to get relationships loaded.
        db_session.refresh(image)

        # Convert to ImageView.
        image_view = ImageView.from_image_table(image=image)

        # Verify multiple annotations and captions.
        assert len(image_view.annotations) == 2
        annotation_sample_ids = {a.sample_id for a in image_view.annotations}
        assert annotation1.sample_id in annotation_sample_ids
        assert annotation2.sample_id in annotation_sample_ids

        assert len(image_view.captions) == 2
        caption_texts = {c.text for c in image_view.captions}
        assert "First caption" in caption_texts
        assert "Second caption" in caption_texts
