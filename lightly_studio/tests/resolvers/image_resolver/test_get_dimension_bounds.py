from sqlmodel import Session

from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    image_resolver,
    tag_resolver,
)
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotations,
    create_dataset,
    create_images,
    create_tag,
)


def test_get_dimension_bounds(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples with different dimensions
    create_images(
        db_session=test_db,
        dataset_id=dataset_id,
        images=[
            ImageStub(path="small.jpg", width=100, height=200),
            ImageStub(path="large.jpg", width=1920, height=1080),
        ],
    )

    bounds = image_resolver.get_dimension_bounds(session=test_db, dataset_id=dataset_id)
    assert bounds["min_width"] == 100
    assert bounds["max_width"] == 1920
    assert bounds["min_height"] == 200
    assert bounds["max_height"] == 1080


def test_get_dimension_bounds__with_tag_filtering(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    # Create samples with different dimensions
    images = create_images(
        db_session=test_db,
        dataset_id=dataset_id,
        images=[
            ImageStub(path="small.jpg", width=100, height=200),
            ImageStub(path="medium.jpg", width=800, height=600),
            ImageStub(path="large.jpg", width=1920, height=1080),
        ],
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
        sample_ids=[images[1].sample_id, images[2].sample_id],
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
        sample_ids=[images[0].sample_id, images[1].sample_id],
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
    images = create_images(
        db_session=test_db,
        dataset_id=dataset_id,
        images=[
            ImageStub(path="small.jpg", width=100, height=200),
            ImageStub(path="medium.jpg", width=500, height=600),
            ImageStub(path="large.jpg", width=1920, height=1080),
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

    # Add annotations:
    # - small image has dog
    # - medium image has both dog and cat
    # - large image has cat
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
                annotation_label_id=dog_label.annotation_label_id,
                x=250,
                y=300,
                width=30,
                height=30,
            ),
            AnnotationDetails(
                sample_id=images[1].sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                x=250,
                y=300,
                width=40,
                height=40,
            ),
            AnnotationDetails(
                sample_id=images[2].sample_id,
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
