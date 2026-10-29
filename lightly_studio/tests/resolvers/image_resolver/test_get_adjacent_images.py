from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import image_resolver, metadata_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails, ImageStub
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    SampleMetricStub,
    create_run,
    create_sample_metrics,
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
        set_as_default=True,
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
        order_by=[OrderByMetadataField("score")],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_a.sample_id


def test_get_adjacent_images__sort_by_numeric_metadata_field_without_cast(
    db_session: Session,
) -> None:
    """Numeric metadata sorts numerically without the caller declaring the type."""
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

    # Numeric order: b(9) < c(10) < a(100). Lexicographically it would be c, a, b.
    metadata_resolver.bulk_update_metadata(
        db_session,
        [
            (image_a.sample_id, {"score": 100}),
            (image_b.sample_id, {"score": 9}),
            (image_c.sample_id, {"score": 10}),
        ],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        order_by=[OrderByMetadataField("score")],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_a.sample_id


def test_get_adjacent_images__sort_by_evaluation_metric(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    run = create_run(session=db_session, collection_id=collection_id)
    image_a = helpers_resolvers.create_image(session=db_session, collection_id=collection_id)
    image_b = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )

    # score order: b(1) < c(2) < a(3), so sorted sequence is b, c, a
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[
            SampleMetricStub(sample_id=image_a.sample_id, metrics={"score": 3.0}),
            SampleMetricStub(sample_id=image_b.sample_id, metrics={"score": 1.0}),
            SampleMetricStub(sample_id=image_c.sample_id, metrics={"score": 2.0}),
        ],
    )

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


def test_get_adjacent_images__respects_embedding_region(db_session: Session) -> None:
    collection_id, images = _setup_collection_with_2d_coordinates(
        session=db_session,
        paths_and_embeddings=[
            ("/images/a.png", [1.0, 0.0]),
            ("/images/b.png", [1.0, 0.0]),
            ("/images/c.png", [1.0, 0.0]),
        ],
        coordinates=[(1.0, 1.0), (100.0, 100.0), (5.0, 5.0)],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=images[0].sample_id,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                embedding_region=_square(x_min=0, y_min=0, x_max=10, y_max=10)
            )
        ),
    )

    # b.png is outside the region, so c.png follows a.png.
    assert result is not None
    assert result.previous_sample_id is None
    assert result.next_sample_id == images[2].sample_id
    assert result.current_sample_position == 1
    assert result.total_count == 2


def test_get_adjacent_images__with_similarity_and_embedding_region(db_session: Session) -> None:
    collection_id, images = _setup_collection_with_2d_coordinates(
        session=db_session,
        paths_and_embeddings=[
            ("/images/a.png", [0.0, 1.0]),
            ("/images/b.png", [1.0, 1.0]),
            ("/images/c.png", [1.0, 0.0]),
        ],
        coordinates=[(1.0, 1.0), (100.0, 100.0), (5.0, 5.0)],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=images[2].sample_id,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                embedding_region=_square(x_min=0, y_min=0, x_max=10, y_max=10)
            )
        ),
        text_embedding=[1.0, 0.0],
    )

    # b.png is the second most similar image but is outside the region.
    assert result is not None
    assert result.previous_sample_id is None
    assert result.next_sample_id == images[0].sample_id
    assert result.current_sample_position == 1
    assert result.total_count == 2


def test_get_adjacent_images__with_similarity_follows_grid_order(db_session: Session) -> None:
    collection_id, images = _setup_collection_with_2d_coordinates(
        session=db_session,
        paths_and_embeddings=[
            ("/images/a.png", [0.0, 1.0]),
            ("/images/b.png", [1.0, 0.0]),
            ("/images/c.png", [1.0, 1.0]),
            ("/images/d.png", [1.0, 0.0]),
        ],
        coordinates=[(1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0)],
    )
    text_embedding = [1.0, 0.0]

    grid = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )
    grid_ids = [sample.sample_id for sample in grid.samples]
    # b.png and d.png tie on similarity and keep the path order.
    assert grid_ids == [
        images[1].sample_id,
        images[3].sample_id,
        images[2].sample_id,
        images[0].sample_id,
    ]

    next_ids = []
    for sample_id in grid_ids:
        result = image_resolver.get_adjacent_images(
            session=db_session,
            sample_id=sample_id,
            collection_id=collection_id,
            text_embedding=text_embedding,
        )
        assert result is not None
        next_ids.append(result.next_sample_id)
    assert next_ids == [*grid_ids[1:], None]


def _square(x_min: float, y_min: float, x_max: float, y_max: float) -> EmbeddingRegion:
    return EmbeddingRegion(
        polygon=[
            Point2D(x=x_min, y=y_min),
            Point2D(x=x_max, y=y_min),
            Point2D(x=x_max, y=y_max),
            Point2D(x=x_min, y=y_max),
        ]
    )


def _setup_collection_with_2d_coordinates(
    session: Session,
    paths_and_embeddings: list[tuple[str, list[float]]],
    coordinates: list[tuple[float, float]],
) -> tuple[UUID, list[ImageTable]]:
    """Create images with embeddings and cached 2D plot coordinates, in input order."""
    collection = helpers_resolvers.create_collection(session=session)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=session,
        collection_id=collection.collection_id,
        embedding_dimension=2,
        set_as_default=True,
    )
    images = helpers_resolvers.create_samples_with_embeddings(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path=path), embedding) for path, embedding in paths_and_embeddings
        ],
    )
    helpers_resolvers.create_saved_plot(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        coordinates={image.sample_id: xy for image, xy in zip(images, coordinates)},
    )
    return collection.collection_id, images
