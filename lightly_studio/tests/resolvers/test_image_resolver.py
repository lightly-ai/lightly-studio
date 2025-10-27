import pytest
from pydantic_core._pydantic_core import ValidationError
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    image_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.samples_filter import (
    FilterDimensions,
    SampleFilter,
)
from tests.helpers_resolvers import (
    AnnotationDetails,
    SampleImage,
    create_annotations,
    create_dataset,
    create_embedding_model,
    create_image,
    create_sample_embedding,
    create_images,
    create_tag,
)


def test_create_many_samples(test_db: Session) -> None:
    """Test bulk creation of samples."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    samples_to_create = [
        ImageCreate(
            dataset_id=dataset_id,
            file_path_abs=f"/path/to/batch_sample_{i}.png",
            file_name=f"batch_sample_{i}.png",
            width=100 + i * 10,
            height=200 + i * 10,
        )
        for i in range(5)
    ]

    created_samples = image_resolver.create_many(session=test_db, samples=samples_to_create)

    assert len(created_samples) == 5
    # Check if order is preserved
    for i, sample in enumerate(created_samples):
        assert sample.file_name == f"batch_sample_{i}.png"

    retrieved_samples = image_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Check if all samples are really in the database
    assert len(retrieved_samples.samples) == 5
    for i, sample in enumerate(retrieved_samples.samples):
        assert sample.file_name == f"batch_sample_{i}.png"


def test_filter_new_paths(test_db: Session) -> None:
    # 1. Case: empty DB, all paths are new
    dataset = create_dataset(session=test_db)

    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/sample.png"]
    )

    assert file_paths_new == ["/path/to/sample.png"]
    assert file_paths_old == []

    # Case 2: db non empty, same paths are new same are old
    create_image(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/path/to/sample.png",
    )

    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/sample.png", "/path/to/sample_new.png"]
    )

    assert file_paths_new == ["/path/to/sample_new.png"]
    assert file_paths_old == ["/path/to/sample.png"]

    # Case 2: db non empty, only old
    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/sample.png"]
    )

    assert file_paths_new == []
    assert file_paths_old == ["/path/to/sample.png"]

    # Case 3: db non empty, empty request
    file_paths_new, file_paths_old = image_resolver.filter_new_paths(
        session=test_db, file_paths_abs=[]
    )

    assert file_paths_new == []
    assert file_paths_old == []


def test_count_by_dataset_id(test_db: Session) -> None:
    """Test counting samples by dataset ID."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Initially should be 0
    assert image_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 0

    # Create some samples
    for i in range(3):
        create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"/path/to/sample{i}.png",
        )

    # Should now count 3 samples
    assert image_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 3

    # Create another dataset to ensure count is dataset-specific
    dataset2 = create_dataset(session=test_db, dataset_name="dataset2")
    dataset2_id = dataset2.dataset_id

    create_image(
        session=test_db,
        dataset_id=dataset2_id,
        file_path_abs="/path/to/other_sample.png",
    )

    # Counts should be independent
    assert image_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset_id) == 3
    assert image_resolver.count_by_dataset_id(session=test_db, dataset_id=dataset2_id) == 1


def test_get_many_by_id(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    # Create samples.
    sample1 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )
    sample2 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )

    # Act.
    samples = image_resolver.get_many_by_id(
        session=test_db, sample_ids=[sample1.sample_id, sample2.sample_id]
    )

    # Assert.
    assert len(samples) == 2
    assert samples[0].file_name == "sample1.png"
    assert samples[1].file_name == "sample2.png"


def test_get_all_by_dataset_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

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
    dataset_id = dataset.dataset_id

    # Create sample data with known sample_ids to ensure consistent ordering
    samples = []
    for i in range(5):  # Create 5 samples
        sample = create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"/sample{i}.png",
            width=100 + i,
            height=100 + i,
        )
        samples.append(sample)

    # Sort samples by sample_id to match the expected order
    samples.sort(key=lambda x: x.file_name)

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
    assert result_page_1.samples[0].file_name == samples[0].file_name
    assert result_page_1.samples[1].file_name == samples[1].file_name

    # Assert - Check second page
    assert len(result_page_2.samples) == 2
    assert result_page_2.total_count == 5
    assert result_page_2.samples[0].file_name == samples[2].file_name
    assert result_page_2.samples[1].file_name == samples[3].file_name

    # Assert - Check third page (should return 1 sample)
    assert len(result_page_3.samples) == 1
    assert result_page_3.total_count == 5
    assert result_page_3.samples[0].file_name == samples[4].file_name

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
    dataset_id = dataset.dataset_id

    # Act
    result = image_resolver.get_all_by_dataset_id(session=test_db, dataset_id=dataset_id)

    # Assert
    assert len(result.samples) == 0  # Should return an empty list
    assert result.total_count == 0


def test_get_all_by_dataset_id__with_annotation_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples
    sample1 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample1.png",
            file_name="sample1.png",
            width=100,
            height=100,
        ),
    )
    sample2 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample2.png",
            file_name="sample2.png",
            width=200,
            height=200,
        ),
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
                sample_id=sample1.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                x=50,
                y=50,
                width=20,
                height=20,
            ),
            AnnotationDetails(
                sample_id=sample2.sample_id,
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
        filters=SampleFilter(annotation_label_ids=[dog_label.annotation_label_id]),
    )
    assert len(dog_result.samples) == 1
    assert dog_result.total_count == 1
    assert dog_result.samples[0].file_name == "sample1.png"

    # Test filtering by cat
    cat_result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(annotation_label_ids=[cat_label.annotation_label_id]),
    )
    assert len(cat_result.samples) == 1
    assert cat_result.total_count == 1
    assert cat_result.samples[0].file_name == "sample2.png"

    # Test filtering by both
    all_result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(
            annotation_label_ids=[
                dog_label.annotation_label_id,
                cat_label.annotation_label_id,
            ]
        ),
    )
    assert len(all_result.samples) == 2
    assert all_result.total_count == 2


def test_get_all_by_dataset_id__with_sample_ids(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples
    image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample1.png",
            file_name="sample1.png",
            width=100,
            height=100,
        ),
    )
    sample2 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample2.png",
            file_name="sample2.png",
            width=200,
            height=200,
        ),
    )
    sample3 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample3.png",
            file_name="sample3.png",
            width=200,
            height=200,
        ),
    )
    sample_ids = [sample2.sample_id, sample3.sample_id]

    result = image_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id, sample_ids=sample_ids
    )
    # Assert all requested sample IDs are in the returned samples.
    returned_sample_ids = [sample.sample_id for sample in result.samples]
    assert len(result.samples) == len(sample_ids)
    assert result.total_count == len(sample_ids)
    assert all(sample_id in returned_sample_ids for sample_id in sample_ids)


def test_get_dimension_bounds(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples with different dimensions
    image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample1.png",
            file_name="small.jpg",
            width=100,
            height=200,
        ),
    )
    image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample2.png",
            file_name="large.jpg",
            width=1920,
            height=1080,
        ),
    )

    bounds = image_resolver.get_dimension_bounds(session=test_db, dataset_id=dataset_id)
    assert bounds["min_width"] == 100
    assert bounds["max_width"] == 1920
    assert bounds["min_height"] == 200
    assert bounds["max_height"] == 1080


def test_get_all_by_dataset_id__with_dimension_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples with different dimensions
    image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample1.png",
            file_name="small.jpg",
            width=100,
            height=200,
        ),
    )
    image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample2.png",
            file_name="medium.jpg",
            width=800,
            height=600,
        ),
    )
    image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample3.png",
            file_name="large.jpg",
            width=1920,
            height=1080,
        ),
    )

    # Test width filtering
    result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(
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
        filters=SampleFilter(
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
        filters=SampleFilter(
            width=FilterDimensions(min=500, max=1000),
            height=FilterDimensions(min=500),
        ),
    )
    assert len(result.samples) == 1
    assert result.total_count == 1
    assert result.samples[0].file_name == "medium.jpg"


def test_get_dimension_bounds__with_tag_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples with different dimensions
    sample1 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/small.png",
            file_name="small.jpg",
            width=100,
            height=200,
        ),
    )
    sample2 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/medium.png",
            file_name="medium.jpg",
            width=800,
            height=600,
        ),
    )
    sample3 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/large.png",
            file_name="large.jpg",
            width=1920,
            height=1080,
        ),
    )

    # create tag of medium->large images
    tag_bigger = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="bigger",
        kind="sample",
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_bigger.tag_id,
        sample_ids=[sample2.sample_id, sample3.sample_id],
    )

    # create tag of medium->small images
    tag_smaller = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="smaller",
        kind="sample",
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_smaller.tag_id,
        sample_ids=[sample1.sample_id, sample2.sample_id],
    )

    # Test width filtering of bigger samples
    bounds = image_resolver.get_dimension_bounds(
        session=test_db, dataset_id=dataset_id, tag_ids=[tag_bigger.tag_id]
    )
    assert bounds["min_width"] == 800
    assert bounds["max_width"] == 1920
    assert bounds["min_height"] == 600
    assert bounds["max_height"] == 1080

    # Test height filtering of smaller samples
    bounds = image_resolver.get_dimension_bounds(
        session=test_db, dataset_id=dataset_id, tag_ids=[tag_smaller.tag_id]
    )
    assert bounds["min_width"] == 100
    assert bounds["max_width"] == 800
    assert bounds["min_height"] == 200
    assert bounds["max_height"] == 600


def test_get_dimension_bounds_with_annotation_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples with different dimensions
    sample1 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample1.png",
            file_name="small.jpg",
            width=100,
            height=200,
        ),
    )
    sample2 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample2.png",
            file_name="medium.jpg",
            width=500,
            height=600,
        ),
    )
    sample3 = image_resolver.create(
        session=test_db,
        sample=ImageCreate(
            dataset_id=dataset_id,
            file_path_abs="/path/to/sample3.png",
            file_name="large.jpg",
            width=1920,
            height=1080,
        ),
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

    # Add annotations:
    # - small image has dog
    # - medium image has both dog and cat
    # - large image has cat
    create_annotations(
        session=test_db,
        dataset_id=dataset_id,
        annotations=[
            AnnotationDetails(
                sample_id=sample1.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                x=50,
                y=50,
                width=20,
                height=20,
            ),
            AnnotationDetails(
                sample_id=sample2.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
                x=250,
                y=300,
                width=30,
                height=30,
            ),
            AnnotationDetails(
                sample_id=sample2.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                x=250,
                y=300,
                width=40,
                height=40,
            ),
            AnnotationDetails(
                sample_id=sample3.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                x=960,
                y=540,
                width=100,
                height=100,
            ),
        ],
    )

    # Test without filtering (should get all samples)
    bounds = image_resolver.get_dimension_bounds(session=test_db, dataset_id=dataset_id)
    assert bounds["min_width"] == 100
    assert bounds["max_width"] == 1920
    assert bounds["min_height"] == 200
    assert bounds["max_height"] == 1080

    # Test filtering by dog (should only get small and medium images)
    dog_bounds = image_resolver.get_dimension_bounds(
        session=test_db,
        dataset_id=dataset_id,
        annotation_label_ids=[dog_label.annotation_label_id],
    )
    assert dog_bounds["min_width"] == 100
    assert dog_bounds["max_width"] == 500
    assert dog_bounds["min_height"] == 200
    assert dog_bounds["max_height"] == 600

    # Test filtering by cat (should only get medium and large images)
    cat_bounds = image_resolver.get_dimension_bounds(
        session=test_db,
        dataset_id=dataset_id,
        annotation_label_ids=[cat_label.annotation_label_id],
    )
    assert cat_bounds["min_width"] == 500
    assert cat_bounds["max_width"] == 1920
    assert cat_bounds["min_height"] == 600
    assert cat_bounds["max_height"] == 1080

    # Test filtering by both dog and cat (should only get medium image)
    both_bounds = image_resolver.get_dimension_bounds(
        session=test_db,
        dataset_id=dataset_id,
        annotation_label_ids=[
            dog_label.annotation_label_id,
            cat_label.annotation_label_id,
        ],
    )
    assert both_bounds["min_width"] == 500
    assert both_bounds["max_width"] == 500
    assert both_bounds["min_height"] == 600
    assert both_bounds["max_height"] == 600


def test_get_dimension_bounds__no_samples(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    bounds = image_resolver.get_dimension_bounds(session=test_db, dataset_id=dataset_id)
    assert bounds == {}


def test_add_tag_to_sample(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag = create_tag(session=test_db, dataset_id=dataset_id, kind="sample")
    sample = create_image(session=test_db, dataset_id=dataset_id)

    # add sample to tag
    tag_resolver.add_tag_to_sample(session=test_db, tag_id=tag.tag_id, sample=sample.sample)

    assert sample.sample.tags.index(tag) == 0


def test_add_tag_to_sample__ensure_correct_kind(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag_with_wrong_kind = create_tag(session=test_db, dataset_id=dataset_id, kind="annotation")
    sample = create_image(session=test_db, dataset_id=dataset_id)

    # adding sample to tag with wrong kind raises ValueError
    with pytest.raises(ValueError, match="is not of kind 'sample'"):
        tag_resolver.add_tag_to_sample(
            session=test_db, tag_id=tag_with_wrong_kind.tag_id, sample=sample.sample
        )


def test_remove_sample_from_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag = create_tag(session=test_db, dataset_id=dataset_id, kind="sample")
    sample = create_image(session=test_db, dataset_id=dataset_id)

    # add sample to tag
    tag_resolver.add_tag_to_sample(session=test_db, tag_id=tag.tag_id, sample=sample.sample)
    assert len(sample.sample.tags) == 1
    assert sample.sample.tags.index(tag) == 0

    # remove sample to tag
    tag_resolver.remove_tag_from_sample(session=test_db, tag_id=tag.tag_id, sample=sample.sample)
    assert len(sample.sample.tags) == 0
    with pytest.raises(ValueError, match="is not in list"):
        sample.sample.tags.index(tag)


def test_add_and_remove_sample_ids_to_tag_id(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag_1 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_all",
        kind="sample",
    )
    tag_2 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_odd",
        kind="sample",
    )

    total_samples = 10
    samples = []
    for i in range(total_samples):
        sample = create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"sample{i}.png",
        )
        samples.append(sample)

    # add samples to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in samples],
    )

    # add every odd samples to tag_2
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_2.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(samples) if i % 2 == 1],
    )

    # ensure all samples were added to the correct tags
    for i, sample in enumerate(samples):
        assert tag_1 in sample.sample.tags
        if i % 2 == 1:
            assert tag_2 in sample.sample.tags

    # ensure the correct number of samples were added to each tag
    assert len(tag_1.samples) == total_samples
    assert len(tag_2.samples) == total_samples / 2

    # Remove the *same* even indexed samples we added earlier,
    # but computed from the original `samples` list so ordering is stable.
    tag_resolver.remove_sample_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[s.sample_id for i, s in enumerate(samples) if i % 2 == 0],
    )

    assert len(tag_1.samples) == total_samples / 2
    assert len(tag_2.samples) == total_samples / 2

    tag_1_samples_sorted = sorted(tag_1.samples, key=lambda s: s.sample_id)
    tag_2_samples_sorted = sorted(tag_2.samples, key=lambda s: s.sample_id)
    assert tag_1_samples_sorted == tag_2_samples_sorted


def test_add_and_remove_sample_ids_to_tag_id__twice_same_sample_ids(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag_1 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_all",
        kind="sample",
    )

    total_samples = 10
    samples = []
    for i in range(total_samples):
        sample = create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"sample{i}.png",
        )
        samples.append(sample)

    # add samples to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in samples],
    )

    # adding the same samples to tag_1 does not create an error
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in samples],
    )

    # ensure all samples were added once
    assert len(tag_1.samples) == total_samples

    # remove samples from
    tag_resolver.remove_sample_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in samples],
    )
    # removing the same samples to tag_1 does not create an error
    tag_resolver.remove_sample_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        sample_ids=[sample.sample_id for sample in samples],
    )

    # ensure all samples were removed again
    assert len(tag_1.samples) == 0


def test_add_and_remove_sample_ids_to_tag_id__ensure_correct_kind(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag_with_wrong_kind = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_with_wrong_kind",
        kind="annotation",
    )

    samples = [
        create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs="sample.png",
        )
    ]

    # adding samples to tag with wrong kind raises ValueError
    with pytest.raises(ValueError, match="is not of kind 'sample'"):
        tag_resolver.add_sample_ids_to_tag_id(
            session=test_db,
            tag_id=tag_with_wrong_kind.tag_id,
            sample_ids=[sample.sample_id for sample in samples],
        )


def test_get_all_by_dataset_id__with_tag_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
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
    samples = []
    for i in range(total_samples):
        sample = create_image(
            session=test_db,
            dataset_id=dataset_id,
            file_path_abs=f"sample{i}.png",
        )
        samples.append(sample)

    # add first half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_part1.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(samples) if i < total_samples / 2],
    )

    # add second half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_part2.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(samples) if i >= total_samples / 2],
    )

    # Test filtering by tags
    result_part1 = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(tag_ids=[tag_part1.tag_id]),
    )
    assert len(result_part1.samples) == int(total_samples / 2)
    assert result_part1.total_count == int(total_samples / 2)
    assert result_part1.samples[0].file_path_abs == "sample0.png"

    result_part2 = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(tag_ids=[tag_part2.tag_id]),
    )
    assert len(result_part2.samples) == int(total_samples / 2)
    assert result_part2.total_count == int(total_samples / 2)
    assert result_part2.samples[0].file_path_abs == "sample5.png"

    # test filtering by both tags
    result_all = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(
            tag_ids=[
                tag_part1.tag_id,
                tag_part2.tag_id,
            ],
        ),
    )
    assert len(result_all.samples) == int(total_samples)
    assert result_all.total_count == int(total_samples)


def test_get_all_by_dataset_id_with_embedding_sort(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="example_embedding_model",
        embedding_dimension=3,
    )
    # create samples
    sample1 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )
    sample2 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )
    sample3 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample3.png",
    )
    create_sample_embedding(
        session=test_db,
        sample_id=sample1.sample_id,
        embedding=[1.0, 1.0, 1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    create_sample_embedding(
        session=test_db,
        sample_id=sample2.sample_id,
        embedding=[-1.0, -1.0, -1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    create_sample_embedding(
        session=test_db,
        sample_id=sample3.sample_id,
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
    assert result.samples[0].sample_id == sample2.sample_id
    assert result.samples[1].sample_id == sample3.sample_id
    assert result.samples[2].sample_id == sample1.sample_id

    # Retrieve Samples ordered by similarity to the provided embedding
    result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        text_embedding=[1.0, 1.0, 1.0],
    )

    # Assert
    assert len(result.samples) == 3
    assert result.total_count == 3
    assert result.samples[0].sample_id == sample1.sample_id
    assert result.samples[1].sample_id == sample3.sample_id
    assert result.samples[2].sample_id == sample2.sample_id


def test_get_all_by_dataset_id__returns_total_count(test_db: Session) -> None:
    """Test that get_all_by_dataset_id returns correct total_count with pagination."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

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
    dataset_id = dataset.dataset_id

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
        filters=SampleFilter(
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
    dataset_id = dataset.dataset_id

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


def test_get_samples_excluding(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # create samples
    sample1 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample1.png",
    )
    sample2 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample2.png",
    )
    sample3 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample3.png",
    )
    sample4 = create_image(
        session=test_db,
        dataset_id=dataset_id,
        file_path_abs="/path/to/sample4.png",
    )

    # Retrieve Samples
    samples = image_resolver.get_samples_excluding(
        session=test_db,
        dataset_id=dataset_id,
        excluded_sample_ids=[sample1.sample_id],
    )

    # Assert
    assert len(samples) == 3
    returned_sample_ids = [sample.sample_id for sample in samples]
    assert sample1.sample_id not in returned_sample_ids
    assert sorted(returned_sample_ids) == sorted(
        [
            sample2.sample_id,
            sample3.sample_id,
            sample4.sample_id,
        ]
    )
    # Retrieve Samples
    samples = image_resolver.get_samples_excluding(
        session=test_db,
        dataset_id=dataset_id,
        excluded_sample_ids=[sample1.sample_id],
        limit=2,
    )

    # Assert
    assert len(samples) == 2


def test_get_all_by_dataset_id__filters_by_sample_ids(test_db: Session) -> None:
    """Selecting explicit sample IDs should restrict the result set."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    created_samples = create_images(
        db_session=test_db,
        dataset_id=dataset_id,
        images=[
            SampleImage(path="sample_0.png"),
            SampleImage(path="sample_1.png"),
            SampleImage(path="sample_2.png"),
            SampleImage(path="sample_3.png"),
        ],
    )

    selected_sample_ids = [
        created_samples[0].sample_id,
        created_samples[2].sample_id,
    ]

    filtered_result = image_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
        filters=SampleFilter(sample_ids=selected_sample_ids),
    )

    result_sample_ids = [sample.sample_id for sample in filtered_result.samples]
    assert result_sample_ids == selected_sample_ids
    assert filtered_result.total_count == len(selected_sample_ids)
