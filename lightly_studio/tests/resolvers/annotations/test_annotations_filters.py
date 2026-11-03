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
    AnnotationsFilter,
    SourceLabelPair,
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


def test_apply_to_parent_sample_query__unannotated_samples(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    annotated = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a")
    unannotated = create_image(session=db_session, collection_id=collection_id, file_path_abs="/b")
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=annotated.sample_id,
        annotation_label_id=cat.annotation_label_id,
    )

    sample_ids = _get_image_sample_ids(
        session=db_session,
        collection_id=collection_id,
        annotations_filter=AnnotationsFilter(include_unannotated_samples=True),
    )

    assert sample_ids == {unannotated.sample_id}


def test_apply_to_parent_sample_query__unannotated_samples_or_label(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    cat_image = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a")
    dog_image = create_image(session=db_session, collection_id=collection_id, file_path_abs="/b")
    unannotated = create_image(session=db_session, collection_id=collection_id, file_path_abs="/c")
    for image, label in [(cat_image, cat), (dog_image, dog)]:
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )

    sample_ids = _get_image_sample_ids(
        session=db_session,
        collection_id=collection_id,
        annotations_filter=AnnotationsFilter(
            annotation_label_ids=[cat.annotation_label_id], include_unannotated_samples=True
        ),
    )

    assert sample_ids == {cat_image.sample_id, unannotated.sample_id}


def test_apply_to_parent_sample_query__unannotated_samples_in_sources(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    in_source_a = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a")
    in_source_b = create_image(session=db_session, collection_id=collection_id, file_path_abs="/b")
    unannotated = create_image(session=db_session, collection_id=collection_id, file_path_abs="/c")
    annotation_a = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=in_source_a.sample_id,
        annotation_label_id=cat.annotation_label_id,
        annotation_collection_name="source_a",
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=in_source_b.sample_id,
        annotation_label_id=cat.annotation_label_id,
        annotation_collection_name="source_b",
    )

    # The image annotated only in source B has no annotation in source A.
    sample_ids = _get_image_sample_ids(
        session=db_session,
        collection_id=collection_id,
        annotations_filter=AnnotationsFilter(
            collection_ids=[annotation_a.annotation_collection_id],
            include_unannotated_samples=True,
        ),
    )

    assert sample_ids == {in_source_b.sample_id, unannotated.sample_id}


class _PairData:
    """Five images annotated in two annotation sources.

    Image "gt_deer" has a deer in ground_truth, "gt_raccoon" a raccoon in ground_truth,
    "model_raccoon" a raccoon in model_v1, "model_deer" a deer in model_v1, and
    "none" has no annotation.
    """

    def __init__(self, session: Session) -> None:
        self.collection_id = create_collection(session=session).collection_id
        self.deer = create_annotation_label(
            session=session, root_collection_id=self.collection_id, label_name="deer"
        ).annotation_label_id
        self.raccoon = create_annotation_label(
            session=session, root_collection_id=self.collection_id, label_name="raccoon"
        ).annotation_label_id
        self.image_ids: dict[str, UUID] = {}
        self.source_ids: dict[str, UUID] = {}
        for name, source, label in [
            ("gt_deer", "ground_truth", self.deer),
            ("gt_raccoon", "ground_truth", self.raccoon),
            ("model_raccoon", "model_v1", self.raccoon),
            ("model_deer", "model_v1", self.deer),
            ("none", None, None),
        ]:
            image = create_image(
                session=session, collection_id=self.collection_id, file_path_abs=f"/{name}"
            )
            self.image_ids[name] = image.sample_id
            if source is None or label is None:
                continue
            annotation = create_annotation(
                session=session,
                collection_id=self.collection_id,
                sample_id=image.sample_id,
                annotation_label_id=label,
                annotation_collection_name=source,
            )
            self.source_ids[source] = annotation.annotation_collection_id

    def pair(self, source: str, label_id: UUID) -> SourceLabelPair:
        return SourceLabelPair(
            collection_id=self.source_ids[source], annotation_label_id=label_id
        )

    def names(self, sample_ids: set[UUID]) -> set[str]:
        return {name for name, sample_id in self.image_ids.items() if sample_id in sample_ids}


def test_pairs__one_pair(db_session: Session) -> None:
    data = _PairData(session=db_session)
    pairs_filter = AnnotationsFilter(source_label_pairs=[data.pair("ground_truth", data.deer)])

    assert _image_names(session=db_session, data=data, annotations_filter=pairs_filter) == {
        "gt_deer"
    }
    assert _annotation_image_names(
        session=db_session, data=data, annotations_filter=pairs_filter
    ) == {"gt_deer"}


def test_pairs__two_pairs_or(db_session: Session) -> None:
    data = _PairData(session=db_session)
    pairs_filter = AnnotationsFilter(
        source_label_pairs=[
            data.pair("ground_truth", data.deer),
            data.pair("model_v1", data.raccoon),
        ]
    )

    assert _image_names(session=db_session, data=data, annotations_filter=pairs_filter) == {
        "gt_deer",
        "model_raccoon",
    }
    assert _annotation_image_names(
        session=db_session, data=data, annotations_filter=pairs_filter
    ) == {"gt_deer", "model_raccoon"}


def test_pairs__mismatched_pair_excluded(db_session: Session) -> None:
    data = _PairData(session=db_session)
    pairs_filter = AnnotationsFilter(
        source_label_pairs=[
            data.pair("ground_truth", data.deer),
            data.pair("model_v1", data.raccoon),
        ]
    )

    # A raccoon in ground_truth and a deer in model_v1 match a class and a source,
    # but not one pair.
    image_names = _image_names(session=db_session, data=data, annotations_filter=pairs_filter)
    annotation_names = _annotation_image_names(
        session=db_session, data=data, annotations_filter=pairs_filter
    )
    assert "gt_raccoon" not in image_names
    assert "model_deer" not in image_names
    assert "gt_raccoon" not in annotation_names
    assert "model_deer" not in annotation_names


def test_pairs__with_unannotated_samples(db_session: Session) -> None:
    data = _PairData(session=db_session)
    pairs_filter = AnnotationsFilter(
        source_label_pairs=[data.pair("ground_truth", data.deer)],
        include_unannotated_samples=True,
    )

    assert _image_names(session=db_session, data=data, annotations_filter=pairs_filter) == {
        "gt_deer",
        "none",
    }


def _image_names(
    session: Session, data: _PairData, annotations_filter: AnnotationsFilter
) -> set[str]:
    return data.names(
        _get_image_sample_ids(
            session=session,
            collection_id=data.collection_id,
            annotations_filter=annotations_filter,
        )
    )


def _annotation_image_names(
    session: Session, data: _PairData, annotations_filter: AnnotationsFilter
) -> set[str]:
    annotations = annotations_resolver.get_all(session=session, filters=annotations_filter)
    return data.names({annotation.parent_sample_id for annotation in annotations.annotations})


def _get_image_sample_ids(
    session: Session, collection_id: UUID, annotations_filter: AnnotationsFilter
) -> set[UUID]:
    return image_resolver.get_sample_ids(
        session=session,
        collection_id=collection_id,
        filters=ImageFilter(sample_filter=SampleFilter(annotations_filter=annotations_filter)),
    )


def _count_sample_joins(query: SelectOfScalar[UUID]) -> int:
    """Count how many times ``sample`` is joined in the compiled query."""
    sql = str(query.compile(compile_kwargs={"literal_binds": True})).lower()
    return sql.count("join sample")
