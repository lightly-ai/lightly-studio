from sqlmodel import Session

from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import get_adjacent_images
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def test_get_adjacent_images_orders_by_path(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    image_a = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    result = get_adjacent_images(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_b.sample_id,
    )

    assert result.sample_previous_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.sample_next_id == image_c.sample_id
    assert result.position == 1


def test_get_adjacent_images_respects_sample_ids(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    result = get_adjacent_images(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_c.sample_id,
        sample_ids=[image_b.sample_id, image_c.sample_id],
    )

    assert result.sample_previous_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.sample_next_id is None
    assert result.position == 1


def test_get_adjacent_images_respects_annotation_filter(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    dog_label = create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="dog",
    )
    cat_label = create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="cat",
    )

    image_a = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    create_annotations(
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

    result = get_adjacent_images(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_b.sample_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(annotation_label_ids=[dog_label.annotation_label_id])
        ),
    )

    assert result.sample_previous_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.sample_next_id is None
    assert result.position == 1


def test_get_adjacent_images_respects_sample_ids_with_similarity(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding-for-adjacency",
        embedding_dimension=2,
    )

    image_a = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    create_sample_embedding(
        session=test_db,
        sample_id=image_a.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 1.0],
    )
    create_sample_embedding(
        session=test_db,
        sample_id=image_b.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.5, 1.0],
    )
    create_sample_embedding(
        session=test_db,
        sample_id=image_c.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 1.0],
    )

    result = get_adjacent_images(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_c.sample_id,
        text_embedding=[1.0, 1.0],
        sample_ids=[image_a.sample_id, image_c.sample_id],
    )

    assert result.sample_previous_id == image_a.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.sample_next_id is None
    assert result.position == 1
