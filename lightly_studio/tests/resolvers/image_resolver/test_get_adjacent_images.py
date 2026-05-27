from sqlmodel import Session

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.resolvers import image_resolver, metadata_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    create_run_and_image,
    insert_metrics,
)


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


def test_get_adjacent_images__distance_is_primary_over_order_by(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding-tiebreaker",
        embedding_dimension=2,
    )

    # image_a and image_b share the same width but differ in similarity to the query
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
        width=100,
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
        width=100,
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
        width=200,
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
        embedding=[-1.0, 0.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_c.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 1.0],
    )

    # Distance is primary: image_a (d=0), image_c (d=1), image_b (d=2).
    # order_by width does not override distance ordering.
    # image_b's previous is image_c, next is None.
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
        text_embedding=[1.0, 0.0],
        order_by=[OrderByField(ImageSampleField.width)],
    )

    assert result is not None
    assert result.previous_sample_id == image_c.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id is None


def test_get_adjacent_images__order_by_is_tiebreaker_when_distances_equal(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding-equal-distances",
        embedding_dimension=2,
    )

    # All images have identical embeddings -> equal distances to any query
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
        width=300,
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
        width=100,
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
        width=200,
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
        embedding=[1.0, 0.0],
    )

    # Distances are equal, so order_by width (asc) breaks the tie:
    # image_b (100), image_c (200), image_a (300).
    # image_c's previous is image_b, next is image_a.
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        text_embedding=[1.0, 0.0],
        order_by=[OrderByField(ImageSampleField.width)],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_a.sample_id


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


def test_get_adjacent_images__sort_by_metadata_field(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/a.png"
    )
    image_b = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )

    # score order: b(1) < c(2) < a(3), so sorted sequence is b, c, a
    metadata_resolver.bulk_update_metadata(
        db_session,
        [
            (image_a.sample_id, {"score": 3}),
            (image_b.sample_id, {"score": 1}),
            (image_c.sample_id, {"score": 2}),
        ],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        order_by=[OrderByMetadataField("score", cast_to_float=True)],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_a.sample_id


def test_get_adjacent_images__sort_by_evaluation_metric(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    run, image_a = create_run_and_image(session=db_session, dataset_collection_id=collection_id)
    image_b = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )

    # score order: b(1) < c(2) < a(3), so sorted sequence is b, c, a
    insert_metrics(db_session, run.id, image_a.sample_id, {"score": 3.0})
    insert_metrics(db_session, run.id, image_b.sample_id, {"score": 1.0})
    insert_metrics(db_session, run.id, image_c.sample_id, {"score": 2.0})

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        order_by=[OrderByEvaluationMetricField("test_run", "score")],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_a.sample_id
