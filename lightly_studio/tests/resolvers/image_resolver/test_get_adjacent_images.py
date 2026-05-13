from sqlmodel import Session

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails


def test_get_adjacent_images__orders_by_path(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
    )

    assert result is not None
    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id == image_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_images__respects_sample_ids(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(sample_ids=[image_b.sample_id, image_c.sample_id])
        ),
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_images__respects_annotation_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    dog_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )
    cat_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    helpers_resolvers.create_annotations(
        session=db_session,
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
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[dog_label.annotation_label_id],
                ),
            )
        ),
    )

    assert result is not None
    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_images__with_similarity(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding-for-adjacency",
        embedding_dimension=2,
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_a.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_b.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.5, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_c.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 1.0],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        text_embedding=[1.0, 1.0],
    )

    assert result is not None
    assert result.previous_sample_id is None
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_b.sample_id
    assert result.current_sample_position == 1
    assert result.total_count == 3


def test_get_adjacent_images__sort_by_file_name(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    # Insert in non-sorted order to verify sorting is applied
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    # Sorted order is a, b, c — so image_b's previous is a, next is c
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.file_name)],
    )

    assert result is not None
    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id == image_c.sample_id


def test_get_adjacent_images__sort_by_file_name_desc(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    # Insert in non-sorted order to verify sorting is applied
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    # Descending: sorted order is c, b, a — so image_b's previous is c, next is a
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.file_name).desc()],
    )

    assert result is not None
    assert result.previous_sample_id == image_c.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id == image_a.sample_id


def test_get_adjacent_images__with_similarity_and_order_by(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding-for-adjacency-order",
        embedding_dimension=2,
    )

    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )

    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_a.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 0.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_b.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 0.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_c.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[-1.0, 0.0],
    )

    # With query [1.0, 0.0]: image_a and image_b are tied (same embedding),
    # order_by file_name asc places image_a before image_b, image_c is last.
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
        text_embedding=[1.0, 0.0],
        order_by=[OrderByField(ImageSampleField.file_name)],
    )

    assert result is not None
    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id == image_c.sample_id


def test_get_adjacent_images__sort_by_width_desc_with_duplicate_values(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
        width=1920,
    )
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
        width=1920,
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
        width=1080,
    )

    # Both image_a and image_b have width=1920. The secondary tiebreaker is file_path_abs DESC
    # (matching the primary direction), so b.png comes before a.png.
    # Order: b.png (1920), a.png (1920), c.png (1080)
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_a.sample_id,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.width).desc()],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_a.sample_id
    assert result.next_sample_id == image_c.sample_id


def test_get_adjacent_images__returns_none_when_sample_not_in_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_1 = helpers_resolvers.create_collection(
        session=db_session, collection_name="collection_1"
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/a.png",
    )
    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/b.png",
    )

    # Use a filter that includes only samples from collection_1,
    # which does not include image_a.sample_id
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_a.sample_id,
        collection_id=collection_1.collection_id,
    )

    assert result is None
