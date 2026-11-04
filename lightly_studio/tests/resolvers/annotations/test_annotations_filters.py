"""Tests for annotation filtering functionality."""

from __future__ import annotations

import uuid
from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver, image_resolver
from lightly_studio.resolvers import annotation_resolver as annotations_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationPair,
    AnnotationsFilter,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.region_sample_ids_filter import RegionSampleIdsFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)


def test_build_sample_ids_query__unfiltered_joins_sample_once() -> None:
    """An empty filter must not add the predicate-only aliased ``sample`` join."""
    query = AnnotationsFilter().build_sample_ids_query(collection_id=uuid.uuid4())

    assert _count_sample_joins(query) == 1


def test_build_sample_ids_query__filtered_joins_sample_for_predicates() -> None:
    """A filter with predicates still joins ``sample`` to apply them."""
    query = AnnotationsFilter(
        annotation_types=[AnnotationType.OBJECT_DETECTION]
    ).build_sample_ids_query(collection_id=uuid.uuid4())

    assert _count_sample_joins(query) == 2


@pytest.fixture
def filter_test_data(
    db_session: Session,
) -> tuple[AnnotationBaseTable, AnnotationBaseTable]:
    """Create test data for filter tests."""
    # Create collections
    collection1 = create_collection(session=db_session)
    collection2 = create_collection(session=db_session, collection_name="collection2")

    # Create samples
    image1 = create_image(
        session=db_session,
        collection_id=collection1.collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=db_session,
        collection_id=collection2.collection_id,
        file_path_abs="/path/to/sample2.png",
    )

    # Create labels
    label1 = create_annotation_label(
        session=db_session, root_collection_id=collection1.collection_id, label_name="label1"
    )
    label2 = create_annotation_label(
        session=db_session, root_collection_id=collection2.collection_id, label_name="label2"
    )

    # Create tags
    tag1 = create_tag(session=db_session, collection_id=collection1.collection_id, tag_name="tag1")
    tag2 = create_tag(session=db_session, collection_id=collection2.collection_id, tag_name="tag2")

    # Create annotations for collection1
    annotation1_id = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection1.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label1.annotation_label_id,
                parent_sample_id=image1.sample_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                x=0,
                y=0,
                width=100,
                height=100,
            )
        ],
    )[0]
    # Create annotations for collection2
    annotation2_id = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection2.collection_id,
        annotations=[
            AnnotationCreate(
                annotation_label_id=label2.annotation_label_id,
                parent_sample_id=image2.sample_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                segmentation_mask=[1, 2, 3, 4, 5],
                x=0,
                y=0,
                width=100,
                height=100,
            ),
        ],
    )[0]
    annotation1 = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation1_id)
    assert annotation1
    annotation2 = annotation_resolver.get_by_id(session=db_session, annotation_id=annotation2_id)
    assert annotation2

    # Add tags to annotations
    annotation1.sample.tags.append(tag1)
    annotation2.sample.tags.append(tag2)
    db_session.commit()

    return annotation1, annotation2


def test_filter_by_collection(
    db_session: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test filtering annotations by collection."""
    annotation1, _ = filter_test_data

    # Test filtering by collection
    collection_filter = AnnotationsFilter(collection_ids=[annotation1.sample.collection_id])
    filtered_annotations = annotations_resolver.get_all(
        session=db_session, filters=collection_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].sample.collection_id == annotation1.sample.collection_id


def test_filter_by_label(
    db_session: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test filtering annotations by label."""
    annotation1, _ = filter_test_data

    # Test filtering by label
    label_filter = AnnotationsFilter(annotation_label_ids=[annotation1.annotation_label_id])
    filtered_annotations = annotations_resolver.get_all(
        session=db_session, filters=label_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].annotation_label_id == annotation1.annotation_label_id


def test_filter_by_tag(
    db_session: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test filtering annotations by tag."""
    annotation1, _ = filter_test_data

    # Test filtering by tag
    tag_filter = AnnotationsFilter(tag_ids=[annotation1.sample.tags[0].tag_id])
    filtered_annotations = annotations_resolver.get_all(
        session=db_session, filters=tag_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].sample_id == annotation1.sample_id


def test_pagination(
    db_session: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],  # noqa: ARG001
) -> None:
    """Test pagination of annotations."""
    # Test pagination
    pagination = Paginated(offset=0, limit=1)
    paginated_annotations = annotations_resolver.get_all(
        session=db_session, pagination=pagination
    ).annotations
    assert len(paginated_annotations) == 1


def test_combined_filters(
    db_session: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
) -> None:
    """Test combining multiple filters."""
    annotation1, _ = filter_test_data

    # Test combined filters
    combined_filter = AnnotationsFilter(
        collection_ids=[annotation1.sample.collection_id],
        annotation_label_ids=[annotation1.annotation_label_id],
        annotation_tag_ids=[annotation1.sample.tags[0].tag_id],
    )
    filtered_annotations = annotations_resolver.get_all(
        session=db_session, filters=combined_filter
    ).annotations
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].sample_id == annotation1.sample_id


def test_filter_delegates_region_filtering_to_mixin(
    db_session: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],
    mocker: MockerFixture,
) -> None:
    """``apply`` must delegate region filtering to the shared mixin and propagate its result.

    It passes the aliased annotation-sample id column; the branch semantics themselves
    are covered by the mixin's own tests in tests/resolvers/test_region_sample_ids_filter.py.
    """
    annotation1, _ = filter_test_data
    spy = mocker.spy(RegionSampleIdsFilter, "_apply_region_sample_ids_filter")

    region_filter = AnnotationsFilter(region_sample_ids=[annotation1.sample_id])
    filtered_annotations = annotations_resolver.get_all(
        session=db_session, filters=region_filter
    ).annotations

    # ``get_all`` issues both a count and a data query, so ``apply`` (and the delegation)
    # runs more than once; every call must pass the annotation-sample id column.
    assert spy.called
    assert all(call.kwargs["sample_id_column"].key == "sample_id" for call in spy.call_args_list)
    assert len(filtered_annotations) == 1
    assert filtered_annotations[0].sample_id == annotation1.sample_id


def test_annotation_pairs__keeps_same_class_in_other_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    car = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    labels_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=car.annotation_label_id,
        annotation_collection_name="labels",
    )
    model_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=car.annotation_label_id,
        annotation_collection_name="model_v1",
    )

    annotations = annotations_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            annotation_pairs=[
                AnnotationPair(
                    collection_id=model_annotation.sample.collection_id,
                    annotation_label_id=car.annotation_label_id,
                )
            ]
        ),
    ).annotations

    assert labels_annotation.sample.collection_id != model_annotation.sample.collection_id
    assert [a.sample_id for a in annotations] == [model_annotation.sample_id]


def test_annotation_pairs__empty_list_matches_nothing(
    db_session: Session,
    filter_test_data: tuple[AnnotationBaseTable, AnnotationBaseTable],  # noqa: ARG001
) -> None:
    annotations = annotations_resolver.get_all(
        session=db_session, filters=AnnotationsFilter(annotation_pairs=[])
    ).annotations

    assert annotations == []


def test_annotation_pairs__parent_sample_query(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    car = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    person = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="person"
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=car.annotation_label_id,
        annotation_collection_name="labels",
    )
    source_id = annotation.sample.collection_id

    def _matching_images(label_id: UUID) -> list[UUID]:
        result = image_resolver.get_all_by_collection_id(
            session=db_session,
            collection_id=collection.collection_id,
            filters=ImageFilter(
                sample_filter=SampleFilter(
                    annotations_filter=AnnotationsFilter(
                        annotation_pairs=[
                            AnnotationPair(collection_id=source_id, annotation_label_id=label_id)
                        ]
                    )
                )
            ),
        )
        return [i.sample_id for i in result.samples]

    assert _matching_images(person.annotation_label_id) == []
    assert _matching_images(car.annotation_label_id) == [image.sample_id]


@pytest.fixture
def unannotated_data(db_session: Session) -> tuple[UUID, UUID, UUID, UUID, UUID, UUID]:
    """Image A has car in labels; image B has nothing. Returns ids."""
    collection = create_collection(session=db_session)
    image_a = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/a.jpg"
    )
    image_b = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/b.jpg"
    )
    car = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    labels_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_a.sample_id,
        annotation_label_id=car.annotation_label_id,
        annotation_collection_name="labels",
    )
    model_annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image_b.sample_id,
        annotation_label_id=car.annotation_label_id,
        annotation_collection_name="model_v1",
    )
    # model_v1 annotates only B, so it is unannotated on A.
    return (
        collection.collection_id,
        image_a.sample_id,
        image_b.sample_id,
        car.annotation_label_id,
        labels_annotation.sample.collection_id,
        model_annotation.sample.collection_id,
    )


def _images_matching(
    db_session: Session, collection_id: UUID, annotations_filter: AnnotationsFilter
) -> set[UUID]:
    result = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(annotations_filter=annotations_filter)),
    )
    return {i.sample_id for i in result.samples}


def test_unannotated_collection_ids__any_source(
    db_session: Session, unannotated_data: tuple[UUID, UUID, UUID, UUID, UUID, UUID]
) -> None:
    collection_id, image_a, image_b, _, labels_id, model_id = unannotated_data

    only_labels = AnnotationsFilter(annotation_pairs=[], unannotated_collection_ids=[labels_id])
    only_model = AnnotationsFilter(annotation_pairs=[], unannotated_collection_ids=[model_id])
    both = AnnotationsFilter(annotation_pairs=[], unannotated_collection_ids=[labels_id, model_id])

    assert _images_matching(db_session, collection_id, only_labels) == {image_b}
    assert _images_matching(db_session, collection_id, only_model) == {image_a}
    assert _images_matching(db_session, collection_id, both) == {image_a, image_b}


def test_unannotated_collection_ids__or_with_pairs(
    db_session: Session, unannotated_data: tuple[UUID, UUID, UUID, UUID, UUID, UUID]
) -> None:
    collection_id, image_a, image_b, car_id, labels_id, _ = unannotated_data

    annotations_filter = AnnotationsFilter(
        annotation_pairs=[AnnotationPair(collection_id=labels_id, annotation_label_id=car_id)],
        unannotated_collection_ids=[labels_id],
    )

    assert _images_matching(db_session, collection_id, annotations_filter) == {image_a, image_b}


def test_unannotated_collection_ids__only_field_set(
    db_session: Session, unannotated_data: tuple[UUID, UUID, UUID, UUID, UUID, UUID]
) -> None:
    collection_id, _, image_b, _, labels_id, _ = unannotated_data

    annotations_filter = AnnotationsFilter(unannotated_collection_ids=[labels_id])

    assert _images_matching(db_session, collection_id, annotations_filter) == {image_b}


def test_unannotated_collection_ids__ignored_by_annotation_query(
    db_session: Session, unannotated_data: tuple[UUID, UUID, UUID, UUID, UUID, UUID]
) -> None:
    _, _, _, _, labels_id, _ = unannotated_data
    unfiltered = annotations_resolver.get_all(session=db_session).annotations

    annotations = annotations_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(unannotated_collection_ids=[labels_id]),
    ).annotations

    assert len(unfiltered) == 2
    assert {a.sample_id for a in annotations} == {a.sample_id for a in unfiltered}


def _count_sample_joins(query: SelectOfScalar[UUID]) -> int:
    """Count how many times ``sample`` is joined in the compiled query."""
    sql = str(query.compile(compile_kwargs={"literal_binds": True})).lower()
    return sql.count("join sample")
