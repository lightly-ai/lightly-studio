"""Database integration tests for query_translation.

Each test builds a query expression model, translates it via
``query_translation.to_match_expression``, and executes it against a populated
database through ``DatasetQuery.match``.  One representative operator per field
type keeps the suite focused while still covering the full translation pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    DatetimeExpr,
    EqualityComparisonOperator,
    FieldRef,
    InstanceSegmentationMatchExpr,
    IntegerExpr,
    NotExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    OrExpr,
    StringExpr,
    TagsContainsExpr,
)
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)


def test_to_match_expression__string_eq(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    target = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/target.jpg"
    )
    create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/other.jpg")

    expr = StringExpr(
        field=FieldRef(table="image", name="file_name"),
        operator=EqualityComparisonOperator.EQ,
        value="target.jpg",
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [target.sample_id]


def test_to_match_expression__integer_gt(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/small.jpg", width=100
    )
    big = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/big.jpg", width=800
    )

    expr = IntegerExpr(
        field=FieldRef(table="image", name="width"),
        operator=OrdinalComparisonOperator.GT,
        value=500,
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [big.sample_id]


def test_to_match_expression__datetime_gt(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    cutoff = datetime(2024, 6, 1, tzinfo=timezone.utc)

    old = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/old.jpg")
    old.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db_session.add(old)

    new = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/new.jpg")
    new.created_at = datetime(2024, 12, 1, tzinfo=timezone.utc)
    db_session.add(new)
    db_session.commit()

    expr = DatetimeExpr(
        field=FieldRef(table="image", name="created_at"),
        operator=OrdinalComparisonOperator.GT,
        value=cutoff,
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [new.sample_id]


def test_to_match_expression__tags_contains(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    image1 = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/1.jpg")
    create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/2.jpg")

    tag = create_tag(session=db_session, collection_id=cid, tag_name="reviewed")
    tag_resolver.add_tag_to_sample(session=db_session, tag_id=tag.tag_id, sample=image1.sample)

    expr = TagsContainsExpr(
        field=FieldRef(table="image", name="tags"),
        tag_name="reviewed",
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [image1.sample_id]


def test_to_match_expression__classification_match(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    image1 = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/cat.jpg")
    create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/dog.jpg")

    label = create_annotation_label(session=db_session, root_collection_id=cid, label_name="cat")
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=image1.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    expr = ClassificationMatchExpr(
        subexpr=StringExpr(
            field=FieldRef(table="classification", name="label"),
            operator=EqualityComparisonOperator.EQ,
            value="cat",
        )
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [image1.sample_id]


def test_to_match_expression__object_detection_match(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    image1 = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/1.jpg")
    image2 = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/2.jpg")

    label = create_annotation_label(session=db_session, root_collection_id=cid, label_name="person")
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=image1.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_data={"x": 0, "y": 0, "width": 100, "height": 100},
    )
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=image2.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_data={"x": 0, "y": 0, "width": 10, "height": 10},
    )

    expr = ObjectDetectionMatchExpr(
        subexpr=IntegerExpr(
            field=FieldRef(table="object_detection", name="width"),
            operator=OrdinalComparisonOperator.GT,
            value=50,
        )
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [image1.sample_id]


def test_to_match_expression__instance_segmentation_match(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    image1 = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/1.jpg")
    create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/2.jpg")

    label = create_annotation_label(session=db_session, root_collection_id=cid, label_name="person")
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=image1.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
    )

    expr = InstanceSegmentationMatchExpr(
        subexpr=StringExpr(
            field=FieldRef(table="instance_segmentation", name="label"),
            operator=EqualityComparisonOperator.EQ,
            value="person",
        )
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [image1.sample_id]


def test_to_match_expression__and(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    create_image(
        session=db_session,
        collection_id=cid,
        file_path_abs="/path/to/small_short.jpg",
        width=100,
        height=100,
    )
    target = create_image(
        session=db_session,
        collection_id=cid,
        file_path_abs="/path/to/big_tall.jpg",
        width=800,
        height=600,
    )
    create_image(
        session=db_session,
        collection_id=cid,
        file_path_abs="/path/to/big_short.jpg",
        width=800,
        height=100,
    )

    expr = AndExpr(
        children=[
            IntegerExpr(
                field=FieldRef(table="image", name="width"),
                operator=OrdinalComparisonOperator.GT,
                value=500,
            ),
            IntegerExpr(
                field=FieldRef(table="image", name="height"),
                operator=OrdinalComparisonOperator.GT,
                value=500,
            ),
        ]
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [target.sample_id]


def test_to_match_expression__or(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    img_a = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/a.jpg")
    img_b = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/b.jpg")
    create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/c.jpg")

    expr = OrExpr(
        children=[
            StringExpr(
                field=FieldRef(table="image", name="file_name"),
                operator=EqualityComparisonOperator.EQ,
                value="a.jpg",
            ),
            StringExpr(
                field=FieldRef(table="image", name="file_name"),
                operator=EqualityComparisonOperator.EQ,
                value="b.jpg",
            ),
        ]
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert {r.sample_id for r in results} == {img_a.sample_id, img_b.sample_id}


def test_to_match_expression__not(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    create_image(
        session=db_session,
        collection_id=cid,
        file_path_abs="/path/to/small.jpg",
        width=100,
    )
    big = create_image(
        session=db_session,
        collection_id=cid,
        file_path_abs="/path/to/big.jpg",
        width=800,
    )

    expr = NotExpr(
        child=IntegerExpr(
            field=FieldRef(table="image", name="width"),
            operator=OrdinalComparisonOperator.LT,
            value=500,
        )
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [r.sample_id for r in results] == [big.sample_id]
