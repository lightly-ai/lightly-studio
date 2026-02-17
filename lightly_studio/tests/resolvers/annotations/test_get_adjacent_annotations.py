import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests import helpers_resolvers


def test_get_adjacent_annotations__orders_by_path(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="label",
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

    annotation_a = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_collection_id = annotation_a.sample.collection_id
    annotation_b = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_c = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_c.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=test_db,
        sample_id=annotation_b.sample_id,
        filters=AnnotationsFilter(collection_ids=[annotation_collection_id]),
    )

    assert result is not None
    assert result.previous_sample_id == annotation_a.sample_id
    assert result.sample_id == annotation_b.sample_id
    assert result.next_sample_id == annotation_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_annotations__respects_sample_ids(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="label",
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

    annotation_a = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_collection_id = annotation_a.sample.collection_id
    annotation_b = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_c = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_c.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=test_db,
        sample_id=annotation_c.sample_id,
        filters=AnnotationsFilter(
            collection_ids=[annotation_collection_id],
            sample_ids=[image_b.sample_id, image_c.sample_id],
        ),
    )

    assert result is not None
    assert result.previous_sample_id == annotation_b.sample_id
    assert result.sample_id == annotation_c.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_annotations__raises_with_filter_missing_collection_id(
    test_db: Session,
) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.IMAGE)
    collection_id = collection.collection_id

    label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="label",
    )

    image = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )

    annotation = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )

    with pytest.raises(ValueError, match="Collection IDs must be provided in filters."):
        annotation_resolver.get_adjacent_annotations(
            session=test_db,
            sample_id=annotation.sample_id,
            filters=AnnotationsFilter(collection_ids=[]),
        )


def test_get_adjacent_annotations__respects_annotation_filter(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.IMAGE)
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

    annotation_a = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
    )
    annotation_collection_id = annotation_a.sample.collection_id
    annotation_b = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
    )
    helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection_id,
        sample_id=image_c.sample_id,
        annotation_label_id=cat_label.annotation_label_id,
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=test_db,
        sample_id=annotation_b.sample_id,
        filters=AnnotationsFilter(
            collection_ids=[annotation_collection_id],
            annotation_label_ids=[dog_label.annotation_label_id],
        ),
    )

    assert result is not None
    assert result.previous_sample_id == annotation_a.sample_id
    assert result.sample_id == annotation_b.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_annotations__returns_none_when_sample_not_in_filter(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db)
    collection_1 = helpers_resolvers.create_collection(
        session=test_db, collection_name="collection_1"
    )

    dog_label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=collection.collection_id,
        label_name="dog",
    )

    image_a = helpers_resolvers.create_image(
        session=test_db,
        collection_id=collection.collection_id,
        file_path_abs="/images/a.png",
    )

    annotation_a = helpers_resolvers.create_annotation(
        session=test_db,
        collection_id=collection.collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
    )

    result = annotation_resolver.get_adjacent_annotations(
        session=test_db,
        sample_id=annotation_a.sample_id,
        filters=AnnotationsFilter(
            collection_ids=[collection_1.collection_id],
        ),
    )

    assert result is None
