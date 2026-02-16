import pytest
from sqlmodel import Session

from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails


def test_get_adjacent_images_orders_by_path(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    result = image_resolver.get_adjacent_images(
        session=test_db,
        sample_id=image_b.sample_id,
        filters=ImageFilter(sample_filter=SampleFilter(collection_id=collection_id)),
    )

    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id == image_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_images_raises_without_filters(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db)
    collection_id = collection.collection_id

    helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    with pytest.raises(ValueError, match="Collection ID must be provided in filters."):
        image_resolver.get_adjacent_images(
            session=test_db,
            sample_id=image_b.sample_id,
        )


def test_get_adjacent_images_raises_with_filter_missing_collection_id(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db)
    collection_id = collection.collection_id

    image = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )

    with pytest.raises(ValueError, match="Collection ID must be provided in filters."):
        image_resolver.get_adjacent_images(
            session=test_db,
            sample_id=image.sample_id,
            filters=ImageFilter(sample_filter=SampleFilter()),
        )


def test_get_adjacent_images_respects_sample_ids(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db)
    collection_id = collection.collection_id

    helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    result = image_resolver.get_adjacent_images(
        session=test_db,
        sample_id=image_c.sample_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                collection_id=collection_id, sample_ids=[image_b.sample_id, image_c.sample_id]
            )
        ),
    )

    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_images_respects_annotation_filter(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db)
    collection_id = collection.collection_id

    dog_label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="dog",
    )
    cat_label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="cat",
    )

    image_a = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    helpers_resolvers.create_annotations(
        session=test_db,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_c.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )

    result = image_resolver.get_adjacent_images(
        session=test_db,
        sample_id=image_b.sample_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                collection_id=collection_id,
                annotation_label_ids=[dog_label.annotation_label_id],
            )
        ),
    )

    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_images_respects_sample_ids_with_similarity(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db)
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding-for-adjacency",
        embedding_dimension=2,
    )

    image_a = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    helpers_resolvers.create_sample_embedding(
        session=test_db,
        sample_id=image_a.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=test_db,
        sample_id=image_b.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.5, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=test_db,
        sample_id=image_c.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 1.0],
    )

    result = image_resolver.get_adjacent_images(
        session=test_db,
        sample_id=image_c.sample_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                collection_id=collection_id, sample_ids=[image_a.sample_id, image_c.sample_id]
            )
        ),
        text_embedding=[1.0, 1.0],
    )

    assert result.previous_sample_id is None
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_a.sample_id
    assert result.current_sample_position == 1
    assert result.total_count == 2
