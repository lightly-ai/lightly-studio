import pytest
from pydantic_core._pydantic_core import ValidationError
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    image_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.image_filter import (
    FilterDimensions,
    ImageFilter,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotations,
    create_dataset,
    create_embedding_model,
    create_image,
    create_images,
    create_sample_embedding,
    create_tag,
)


def test_get_all_by_dataset_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # create samples out of order to verify ordering by file_path_abs
    create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )
    create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )

    # Act
    result = image_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert result.samples[0].file_name == "sample1.png"
    assert result.samples[1].file_name == "sample2.png"


def test_get_all_by_dataset_id__with_pagination(
    test_db: Session,
) -> None:
    # Arrange
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # Create sample data with known sample_ids to ensure consistent ordering
    images = []
    for i in range(5):  # Create 5 samples
        image = create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"/sample{i}.png",
            width=100 + i,
            height=100 + i,
        )
        images.append(image)

    # Sort samples by sample_id to match the expected order
    images.sort(key=lambda x: x.file_name)

    # Act - Get first 2 samples
    result_page_1 = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=0, limit=2)
    )
    # Act - Get next 2 samples
    result_page_2 = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=2, limit=2)
    )
    # Act - Get remaining samples
    result_page_3 = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=4, limit=2)
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
    result_empty = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=5, limit=2)
    )
    assert len(result_empty.samples) == 0
    assert result_empty.total_count == 5


def test_get_all_by_dataset_id__empty_output(
    test_db: Session,
) -> None:
    # Arrange
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # Act
    result = image_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 0  # Should return an empty list
    assert result.total_count == 0


def test_get_all_by_dataset_id__with_annotation_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # Create samples
    images = create_images(
        db_session=test_db,
        dataset_id=dataset_id,
        images=[
            ImageStub(path="sample1.png"),
            ImageStub(path="sample2.png"),
        ],
    )

    # Create labels
    dog_label = annotation_label_resolver.create(
        session=test_db,
        label=AnnotationLabelCreate(dataset_id=dataset_id, annotation_label_name="dog"),
    )
    cat_label = annotation_label_resolver.create(
        session=test_db,
        label=AnnotationLabelCreate(dataset_id=dataset_id, annotation_label_name="cat"),
    )

    # Add annotations: sample1 has dog, sample2 has cat
    create_annotations(
        session=test_db,
        dataset_id=dataset_id,
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
    result = image_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)
    assert len(result.samples) == 2
    assert result.total_count == 2

    # Test filtering by dog
    dog_result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(annotation_label_ids=[dog_label.annotation_label_id])
        ),
    )
    assert len(dog_result.samples) == 1
    assert dog_result.total_count == 1
    assert dog_result.samples[0].file_name == "sample1.png"

    # Test filtering by cat
    cat_result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(annotation_label_ids=[cat_label.annotation_label_id])
        ),
    )
    assert len(cat_result.samples) == 1
    assert cat_result.total_count == 1
    assert cat_result.samples[0].file_name == "sample2.png"

    # Test filtering by both
    all_result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
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


def test_get_all_by_dataset_id__with_sample_ids(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # Create samples
    images = create_images(
        db_session=test_db,
        dataset_id=dataset_id,
        images=[
            ImageStub(path="sample1.png"),
            ImageStub(path="sample2.png"),
            ImageStub(path="sample3.png"),
        ],
    )
    sample_ids = [images[1].sample_id, images[2].sample_id]

    result = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, sample_ids=sample_ids
    )
    # Assert all requested sample IDs are in the returned samples.
    returned_sample_ids = [sample.sample_id for sample in result.samples]
    assert len(result.samples) == len(sample_ids)
    assert result.total_count == len(sample_ids)
    assert all(sample_id in returned_sample_ids for sample_id in sample_ids)


def test_get_all_by_dataset_id__with_dimension_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # Create samples with different dimensions
    create_images(
        db_session=test_db,
        dataset_id=dataset_id,
        images=[
            ImageStub(path="small.jpg", width=100, height=200),
            ImageStub(path="medium.jpg", width=800, height=600),
            ImageStub(path="large.jpg", width=1920, height=1080),
        ],
    )

    # Test width filtering
    result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(
            width=FilterDimensions(min=500),
        ),
    )
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert all(s.width >= 500 for s in result.samples)

    # Test height filtering
    result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(
            height=FilterDimensions(max=700),
        ),
    )
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert all(s.height <= 700 for s in result.samples)

    # Test combined filtering
    result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(
            width=FilterDimensions(min=500, max=1000),
            height=FilterDimensions(min=500),
        ),
    )
    assert len(result.samples) == 1
    assert result.total_count == 1
    assert result.samples[0].file_name == "medium.jpg"


def test_get_all_by_dataset_id__with_tag_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    tag_part1 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_1",
        kind="sample",
    )
    tag_part2 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_2",
        kind="sample",
    )

    total_samples = 10
    images = []
    for i in range(total_samples):
        image = create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"sample{i}.png",
        )
        images.append(image)

    # add first half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_part1.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i < total_samples / 2],
    )

    # add second half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_part2.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i >= total_samples / 2],
    )

    # Test filtering by tags
    result_part1 = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag_part1.tag_id])),
    )
    assert len(result_part1.samples) == int(total_samples / 2)
    assert result_part1.total_count == int(total_samples / 2)
    assert result_part1.samples[0].file_path_abs == "sample0.png"

    result_part2 = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag_part2.tag_id])),
    )
    assert len(result_part2.samples) == int(total_samples / 2)
    assert result_part2.total_count == int(total_samples / 2)
    assert result_part2.samples[0].file_path_abs == "sample5.png"

    # test filtering by both tags
    result_all = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
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


def test_get_all_by_dataset_id_with_embedding_sort(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="example_embedding_model",
        embedding_dimension=3,
    )
    # create samples
    image1 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )
    image3 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample3.png",
    )
    create_sample_embedding(
        session=test_db,
        sample_id=image1.sample_id,
        embedding=[1.0, 1.0, 1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    create_sample_embedding(
        session=test_db,
        sample_id=image2.sample_id,
        embedding=[-1.0, -1.0, -1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    create_sample_embedding(
        session=test_db,
        sample_id=image3.sample_id,
        embedding=[1.0, 1.0, 2.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    # Retrieve Samples ordered by similarity to the provided embedding
    result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        text_embedding=[-1.0, -1.0, -1.0],
    )

    # Assert
    assert len(result.samples) == 3
    assert result.total_count == 3
    assert result.samples[0].sample_id == image2.sample_id
    assert result.samples[1].sample_id == image3.sample_id
    assert result.samples[2].sample_id == image1.sample_id

    # Retrieve Samples ordered by similarity to the provided embedding
    result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        text_embedding=[1.0, 1.0, 1.0],
    )

    # Assert
    assert len(result.samples) == 3
    assert result.total_count == 3
    assert result.samples[0].sample_id == image1.sample_id
    assert result.samples[1].sample_id == image3.sample_id
    assert result.samples[2].sample_id == image2.sample_id


def test_get_all_by_dataset_id__returns_total_count(test_db: Session) -> None:
    """Test that get_all_by_dataset_id returns correct total_count with pagination."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # Create 5 samples.
    for i in range(5):
        create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"/path/to/sample{i}.png",
        )

    # Test total count without pagination (get all samples).
    result = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=0, limit=10)
    )
    assert len(result.samples) == 5
    assert result.total_count == 5

    # Test pagination with offset - total_count should remain the same.
    result = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, pagination=Paginated(offset=0, limit=2)
    )
    assert len(result.samples) == 2
    assert result.total_count == 5


def test_get_all_by_dataset_id__with_filters_returns_total_count(test_db: Session) -> None:
    """Test that get_all_by_dataset_id returns correct total_count with filtered results."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # Create samples with different dimensions
    create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/small1.png",
        width=100,
        height=100,
    )
    create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/small2.png",
        width=150,
        height=150,
    )
    create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/large1.png",
        width=1000,
        height=1000,
    )
    create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/large2.png",
        width=1200,
        height=1200,
    )

    # Test with dimension filtering - should match 2 small samples.
    result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(
            width=FilterDimensions(max=200),
        ),
        pagination=Paginated(offset=0, limit=1),
    )

    assert len(result.samples) == 1
    assert result.total_count == 2
    assert result.samples[0].width <= 200


def test_get_all_by_dataset_id__limit(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    # Create 20 samples.
    for i in range(20):
        create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"/path/to/sample{i}.png",
        )

    # Retrieve all samples.
    samples = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
    ).samples
    assert len(samples) == 20

    # Retrieve 10 samples.
    samples = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        pagination=Paginated(offset=0, limit=10),
    ).samples
    assert len(samples) == 10

    # Retrieve 1 sample.
    samples = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        pagination=Paginated(offset=0, limit=1),
    ).samples
    assert len(samples) == 1

    # Retrieve 0 samples.
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        samples = image_resolver.get_all_by_dataset_id(
            session=test_db,
            dataset_id=dataset_id,
            pagination=Paginated(offset=0, limit=0),
        ).samples

    # Retrieve 100 samples (more than available).
    samples = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        pagination=Paginated(offset=0, limit=100),
    ).samples
    assert len(samples) == 20

    # Retrieve -1 samples.
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        image_resolver.get_all_by_dataset_id(
            session=test_db,
            dataset_id=dataset_id,
            pagination=Paginated(offset=0, limit=-1),
        )


def test_get_all_by_dataset_id__filters_by_sample_ids(test_db: Session) -> None:
    """Selecting explicit sample IDs should restrict the result set."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    created_images = create_images(
        db_session=test_db,
        dataset_id=dataset_id,
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

    filtered_result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=ImageFilter(sample_filter=SampleFilter(sample_ids=selected_sample_ids)),
    )

    result_sample_ids = [sample.sample_id for sample in filtered_result.samples]
    assert result_sample_ids == selected_sample_ids
    assert filtered_result.total_count == len(selected_sample_ids)
