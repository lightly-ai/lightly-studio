import pytest
from pydantic_core._pydantic_core import ValidationError
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.resolvers import (
    image_resolver,
    metadata_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import (
    FilterDimensions,
    ImageFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
    create_sample_embedding,
    create_tag,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    create_run_and_image,
    insert_metrics,
)


def test_get_all_by_collection_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # create samples out of order to verify ordering by file_path_abs
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )

    # Act
    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id
    )

    # Assert
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert result.samples[0].file_name == "sample1.png"
    assert result.samples[1].file_name == "sample2.png"


def test_get_all_by_collection_id__with_pagination(
    db_session: Session,
) -> None:
    # Arrange
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create sample data with known sample_ids to ensure consistent ordering
    images = []
    for i in range(5):  # Create 5 samples
        image = create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"/sample{i}.png",
            width=100 + i,
            height=100 + i,
        )
        images.append(image)

    # Sort samples by sample_id to match the expected order
    images.sort(key=lambda x: x.file_name)

    # Act - Get first 2 samples
    result_page_1 = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, pagination=Paginated(offset=0, limit=2)
    )
    # Act - Get next 2 samples
    result_page_2 = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, pagination=Paginated(offset=2, limit=2)
    )
    # Act - Get remaining samples
    result_page_3 = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, pagination=Paginated(offset=4, limit=2)
    )

    # Assert - Check first page
    assert len(result_page_1.samples) == 2
    assert result_page_1.total_count == 5
    assert result_page_1.samples[0].file_name == images[0].file_name
    assert result_page_1.samples[1].file_name == images[1].file_name

    # Assert - Check second page
    assert len(result_page_2.samples) == 2
    assert result_page_2.total_count == 5
    assert result_page_2.samples[0].file_name == images[2].file_name
    assert result_page_2.samples[1].file_name == images[3].file_name

    # Assert - Check third page (should return 1 sample)
    assert len(result_page_3.samples) == 1
    assert result_page_3.total_count == 5
    assert result_page_3.samples[0].file_name == images[4].file_name

    # Assert - Check out of bounds (should return empty list)
    result_empty = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, pagination=Paginated(offset=5, limit=2)
    )
    assert len(result_empty.samples) == 0
    assert result_empty.total_count == 5


def test_get_all_by_collection_id__empty_output(
    db_session: Session,
) -> None:
    # Arrange
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Act
    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id
    )

    # Assert
    assert len(result.samples) == 0  # Should return an empty list
    assert result.total_count == 0


def test_get_all_by_collection_id__with_annotation_filtering(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create samples
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="sample1.png"),
            ImageStub(path="sample2.png"),
        ],
    )

    # Create labels
    dog_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )
    cat_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )

    # Add annotations: sample1 has dog, sample2 has cat
    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[0].sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                x=50,
                y=50,
                width=20,
                height=20,
            ),
            AnnotationDetails(
                sample_id=images[1].sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                x=70,
                y=70,
                width=30,
                height=30,
            ),
        ],
    )

    # Test without filtering
    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id
    )
    assert len(result.samples) == 2
    assert result.total_count == 2

    # Test filtering by dog
    dog_result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[dog_label.annotation_label_id]
                )
            )
        ),
    )
    assert len(dog_result.samples) == 1
    assert dog_result.total_count == 1
    assert dog_result.samples[0].file_name == "sample1.png"

    # Test filtering by cat
    cat_result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[cat_label.annotation_label_id]
                )
            )
        ),
    )
    assert len(cat_result.samples) == 1
    assert cat_result.total_count == 1
    assert cat_result.samples[0].file_name == "sample2.png"

    # Test filtering by both
    all_result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                annotation_label_ids=[
                    dog_label.annotation_label_id,
                    cat_label.annotation_label_id,
                ]
            )
        ),
    )
    assert len(all_result.samples) == 2
    assert all_result.total_count == 2


def test_get_all_by_collection_id__with_sample_ids(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create samples
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="sample1.png"),
            ImageStub(path="sample2.png"),
            ImageStub(path="sample3.png"),
        ],
    )
    sample_ids = [images[1].sample_id, images[2].sample_id]

    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, sample_ids=sample_ids
    )
    # Assert all requested sample IDs are in the returned samples.
    returned_sample_ids = [sample.sample_id for sample in result.samples]
    assert len(result.samples) == len(sample_ids)
    assert result.total_count == len(sample_ids)
    assert all(sample_id in returned_sample_ids for sample_id in sample_ids)


def test_get_all_by_collection_id__with_dimension_filtering(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create samples with different dimensions
    create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="small.jpg", width=100, height=200),
            ImageStub(path="medium.jpg", width=800, height=600),
            ImageStub(path="large.jpg", width=1920, height=1080),
        ],
    )

    # Test width filtering
    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            width=FilterDimensions(min=500),
        ),
    )
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert all(s.width >= 500 for s in result.samples)

    # Test height filtering
    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            height=FilterDimensions(max=700),
        ),
    )
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert all(s.height <= 700 for s in result.samples)

    # Test combined filtering
    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            width=FilterDimensions(min=500, max=1000),
            height=FilterDimensions(min=500),
        ),
    )
    assert len(result.samples) == 1
    assert result.total_count == 1
    assert result.samples[0].file_name == "medium.jpg"


def test_get_all_by_collection_id__with_tag_filtering(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    tag_part1 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="tag_1",
        kind="sample",
    )
    tag_part2 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="tag_2",
        kind="sample",
    )

    total_samples = 10
    images = []
    for i in range(total_samples):
        image = create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"sample{i}.png",
        )
        images.append(image)

    # add first half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_part1.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i < total_samples / 2],
    )

    # add second half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_part2.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i >= total_samples / 2],
    )

    # Test filtering by tags
    result_part1 = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag_part1.tag_id])),
    )
    assert len(result_part1.samples) == int(total_samples / 2)
    assert result_part1.total_count == int(total_samples / 2)
    assert result_part1.samples[0].file_path_abs == "sample0.png"

    result_part2 = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag_part2.tag_id])),
    )
    assert len(result_part2.samples) == int(total_samples / 2)
    assert result_part2.total_count == int(total_samples / 2)
    assert result_part2.samples[0].file_path_abs == "sample5.png"

    # test filtering by both tags
    result_all = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                tag_ids=[
                    tag_part1.tag_id,
                    tag_part2.tag_id,
                ],
            )
        ),
    )
    assert len(result_all.samples) == int(total_samples)
    assert result_all.total_count == int(total_samples)


def test_get_all_by_collection_id_with_embedding_sort(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
        embedding_dimension=3,
    )
    # create samples
    image1 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    image3 = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/sample3.png",
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image1.sample_id,
        embedding=[1.0, 1.0, 1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    create_sample_embedding(
        session=db_session,
        sample_id=image2.sample_id,
        embedding=[-1.0, -1.0, -1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    create_sample_embedding(
        session=db_session,
        sample_id=image3.sample_id,
        embedding=[1.0, 1.0, 2.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    # Retrieve Samples ordered by similarity to the provided embedding
    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        text_embedding=[-1.0, -1.0, -1.0],
    )

    # Assert
    assert len(result.samples) == 3
    assert result.total_count == 3
    assert result.samples[0].sample_id == image2.sample_id
    assert result.samples[1].sample_id == image3.sample_id
    assert result.samples[2].sample_id == image1.sample_id
    # Verify similarity scores are returned and in descending order.
    assert result.similarity_scores is not None
    assert len(result.similarity_scores) == 3
    assert result.similarity_scores[0] == pytest.approx(1.0, abs=0.01)
    assert result.similarity_scores[0] >= result.similarity_scores[1]

    # Retrieve Samples ordered by similarity to the provided embedding
    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        text_embedding=[1.0, 1.0, 1.0],
    )

    # Assert
    assert len(result.samples) == 3
    assert result.total_count == 3
    assert result.samples[0].sample_id == image1.sample_id
    assert result.samples[1].sample_id == image3.sample_id
    assert result.samples[2].sample_id == image2.sample_id


def test_get_all_by_collection_id__returns_total_count(db_session: Session) -> None:
    """Test that get_all_by_collection_id returns correct total_count with pagination."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create 5 samples.
    for i in range(5):
        create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"/path/to/sample{i}.png",
        )

    # Test total count without pagination (get all samples).
    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, pagination=Paginated(offset=0, limit=10)
    )
    assert len(result.samples) == 5
    assert result.total_count == 5

    # Test pagination with offset - total_count should remain the same.
    result = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id, pagination=Paginated(offset=0, limit=2)
    )
    assert len(result.samples) == 2
    assert result.total_count == 5


def test_get_all_by_collection_id__with_filters_returns_total_count(db_session: Session) -> None:
    """Test that get_all_by_collection_id returns correct total_count with filtered results."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create samples with different dimensions
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/small1.png",
        width=100,
        height=100,
    )
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/small2.png",
        width=150,
        height=150,
    )
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/large1.png",
        width=1000,
        height=1000,
    )
    create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/path/to/large2.png",
        width=1200,
        height=1200,
    )

    # Test with dimension filtering - should match 2 small samples.
    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(
            width=FilterDimensions(max=200),
        ),
        pagination=Paginated(offset=0, limit=1),
    )

    assert len(result.samples) == 1
    assert result.total_count == 2
    assert result.samples[0].width <= 200


def test_get_all_by_collection_id__limit(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Create 20 samples.
    for i in range(20):
        create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"/path/to/sample{i}.png",
        )

    # Retrieve all samples.
    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == 20

    # Retrieve 10 samples.
    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        pagination=Paginated(offset=0, limit=10),
    ).samples
    assert len(samples) == 10

    # Retrieve 1 sample.
    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        pagination=Paginated(offset=0, limit=1),
    ).samples
    assert len(samples) == 1

    # Retrieve 0 samples.
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        samples = image_resolver.get_all_by_collection_id(
            session=db_session,
            collection_id=collection_id,
            pagination=Paginated(offset=0, limit=0),
        ).samples

    # Retrieve 100 samples (more than available).
    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        pagination=Paginated(offset=0, limit=100),
    ).samples
    assert len(samples) == 20

    # Retrieve -1 samples.
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        image_resolver.get_all_by_collection_id(
            session=db_session,
            collection_id=collection_id,
            pagination=Paginated(offset=0, limit=-1),
        )


def test_get_all_by_collection_id__filters_by_sample_ids(db_session: Session) -> None:
    """Selecting explicit sample IDs should restrict the result set."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    created_images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[
            ImageStub(path="sample_0.png"),
            ImageStub(path="sample_1.png"),
            ImageStub(path="sample_2.png"),
            ImageStub(path="sample_3.png"),
        ],
    )

    selected_sample_ids = [
        created_images[0].sample_id,
        created_images[2].sample_id,
    ]

    filtered_result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(sample_ids=selected_sample_ids)),
    )

    result_sample_ids = [sample.sample_id for sample in filtered_result.samples]
    assert result_sample_ids == selected_sample_ids
    assert filtered_result.total_count == len(selected_sample_ids)


def test_get_all_by_collection_id__sort_by_file_name_asc(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    create_image(session=db_session, collection_id=collection_id, file_path_abs="/images/c.png")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/images/a.png")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/images/b.png")

    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.file_name)],
    )

    assert [s.file_name for s in result.samples] == ["a.png", "b.png", "c.png"]


def test_get_all_by_collection_id__sort_by_file_name_desc(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    create_image(session=db_session, collection_id=collection_id, file_path_abs="/images/c.png")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/images/a.png")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/images/b.png")

    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.file_name).desc()],
    )

    assert [s.file_name for s in result.samples] == ["c.png", "b.png", "a.png"]


def test_get_all_by_collection_id__with_similarity_and_order_by(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
        embedding_dimension=2,
    )

    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/a.png"
    )

    create_sample_embedding(
        session=db_session,
        sample_id=image_a.sample_id,
        embedding=[1.0, 0.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image_b.sample_id,
        embedding=[1.0, 0.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image_c.sample_id,
        embedding=[-1.0, 0.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        text_embedding=[1.0, 0.0],
        order_by=[OrderByField(ImageSampleField.file_name)],
    )

    assert len(result.samples) == 3
    # image_a and image_b are tied by similarity; file_name asc places a before b
    assert result.samples[0].file_name == "a.png"
    assert result.samples[1].file_name == "b.png"
    assert result.samples[2].file_name == "c.png"


def test_get_all_by_collection_id__distance_is_primary_over_order_by(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
        embedding_dimension=2,
    )

    # image_a and image_b share the same width but differ in similarity to the query
    image_a = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
        width=100,
    )
    image_b = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
        width=100,
    )
    image_c = create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
        width=200,
    )

    create_sample_embedding(
        session=db_session,
        sample_id=image_a.sample_id,
        embedding=[1.0, 0.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image_b.sample_id,
        embedding=[-1.0, 0.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=image_c.sample_id,
        embedding=[0.0, 1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        text_embedding=[1.0, 0.0],
        order_by=[OrderByField(ImageSampleField.width)],
    )

    assert len(result.samples) == 3
    # distance is the primary sort: image_a (d=0), image_c (d=1), image_b (d=2).
    # order_by width does not override distance ordering.
    assert result.samples[0].sample_id == image_a.sample_id
    assert result.samples[1].sample_id == image_c.sample_id
    assert result.samples[2].sample_id == image_b.sample_id


def test_get_all_by_collection_id__sort_by_metadata_field_asc(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )

    metadata_resolver.bulk_update_metadata(
        db_session,
        [
            (image_a.sample_id, {"score": 3}),
            (image_b.sample_id, {"score": 1}),
            (image_c.sample_id, {"score": 2}),
        ],
    )

    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        order_by=[OrderByMetadataField("score", cast_to_float=True)],
    )

    assert [s.file_name for s in result.samples] == ["b.png", "c.png", "a.png"]


def test_get_all_by_collection_id__sort_by_width_asc(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    create_image(session=db_session, collection_id=collection_id, file_path_abs="/a.png", width=300)
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/b.png", width=100)
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/c.png", width=200)

    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.width)],
    )

    assert [s.width for s in result.samples] == [100, 200, 300]


def test_get_all_by_collection_id__sort_by_evaluation_metric_asc(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    run, image_a = create_run_and_image(session=db_session, dataset_collection_id=collection_id)
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )

    # score order: b(1) < c(2) < a(3), so ascending sorted sequence is b, c, a
    insert_metrics(db_session, run.id, image_a.sample_id, {"score": 3.0})
    insert_metrics(db_session, run.id, image_b.sample_id, {"score": 1.0})
    insert_metrics(db_session, run.id, image_c.sample_id, {"score": 2.0})

    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        order_by=[OrderByEvaluationMetricField("test_run", "score")],
    )

    assert [s.sample_id for s in result.samples] == [
        image_b.sample_id,
        image_c.sample_id,
        image_a.sample_id,
    ]


def test_get_all_by_collection_id__sort_by_evaluation_metric_desc(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    run, image_a = create_run_and_image(session=db_session, dataset_collection_id=collection_id)
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )

    # score order: b(1) < c(2) < a(3), so descending sorted sequence is a, c, b
    insert_metrics(db_session, run.id, image_a.sample_id, {"score": 3.0})
    insert_metrics(db_session, run.id, image_b.sample_id, {"score": 1.0})
    insert_metrics(db_session, run.id, image_c.sample_id, {"score": 2.0})

    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        order_by=[OrderByEvaluationMetricField("test_run", "score").desc()],
    )

    assert [s.sample_id for s in result.samples] == [
        image_a.sample_id,
        image_c.sample_id,
        image_b.sample_id,
    ]


def test_get_all_by_collection_id__sort_by_height_asc_is_reverse_of_desc(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Two images share the same height (200) to test tiebreaker behaviour.
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/c.png", height=300
    )
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/a.png", height=200
    )
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/b.png", height=200
    )
    create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/d.png", height=100
    )

    result_asc = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.height)],
    )
    result_desc = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.height).desc()],
    )

    asc_paths = [s.file_path_abs for s in result_asc.samples]
    desc_paths = [s.file_path_abs for s in result_desc.samples]

    assert asc_paths == list(reversed(desc_paths))
