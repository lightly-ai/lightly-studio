"""Database tests for illegal cross-context query expressions.

These queries are valid at the Pydantic model level (they parse without error)
but are semantically wrong — for example, using an image field inside a
classification matcher or an annotation field at the top level without a
matcher wrapper.  The tests document the current behaviour so regressions or
future validation improvements are caught.

Illegal queries should be rejected at the user interaction layer (e.g. in the frontend
GUI composer).
"""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.query_expr import (
    ClassificationMatchExpr,
    EqualityComparisonOperator,
    FieldRef,
    IntegerExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    StringExpr,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_to_match_expression__image_field_inside_classification_matcher(
    db_session: Session,
) -> None:
    """image.width inside ClassificationMatchExpr is nonsensical.

    The generated SQL nests ``image.width > 500`` inside
    ``EXISTS (SELECT 1 FROM annotation_base WHERE ...)``.  Because the DB
    engine resolves image.width from the outer query scope, the condition
    evaluates on the image row rather than the annotation — silently producing
    wrong results.
    """
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/wide.jpg", width=800
    )
    label = create_annotation_label(session=db_session, root_collection_id=cid, label_name="cat")
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    expr = ClassificationMatchExpr(
        subexpr=IntegerExpr(
            field=FieldRef(table="image", name="width"),
            operator=OrdinalComparisonOperator.GT,
            value=500,
        )
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    # Wrong: image.width leaks into the EXISTS subquery and is resolved from
    # the outer scope, so the row matches even though the classification
    # annotation has no width concept.
    assert len(results) == 1


def test_to_match_expression__classification_field_inside_object_detection_matcher(
    db_session: Session,
) -> None:
    """classification.label inside ObjectDetectionMatchExpr mixes annotation contexts.

    The label lookup goes through AnnotationBaseTable.annotation_label
    regardless of annotation type, but ObjectDetectionMatchExpr adds
    ``annotation_type = 'OBJECT_DETECTION'`` which correctly rejects the
    classification annotation.
    """
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    image = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/img.jpg")
    label = create_annotation_label(session=db_session, root_collection_id=cid, label_name="dog")

    # Create a classification annotation — NOT object detection.
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    expr = ObjectDetectionMatchExpr(
        subexpr=StringExpr(
            field=FieldRef(table="classification", name="label"),
            operator=EqualityComparisonOperator.EQ,
            value="dog",
        )
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    # The ObjectDetectionMatchExpr adds ``annotation_type = 'OBJECT_DETECTION'``
    # but the actual annotation is CLASSIFICATION, so no rows match.
    assert len(results) == 0


def test_to_match_expression__object_detection_field_at_top_level(
    db_session: Session,
) -> None:
    """object_detection.width at the top level without ObjectDetectionMatchExpr.

    Without the matcher wrapper there is no ``annotation_type`` filter.  The
    generated SQL uses an EXISTS subquery through the .has() relationship, so
    it does not error — but it matches annotations of *any* type whose
    object_detection_annotation row satisfies the condition.
    """
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/img.jpg", width=800
    )
    # Second sample has no annotations at all.
    create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/bare.jpg", width=800
    )
    label = create_annotation_label(session=db_session, root_collection_id=cid, label_name="car")
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_data={"x": 0, "y": 0, "width": 100, "height": 100},
    )

    expr = IntegerExpr(
        field=FieldRef(table="object_detection", name="width"),
        operator=OrdinalComparisonOperator.GT,
        value=50,
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    # Wrong: both samples match (2 instead of 1).  The bare sample without any
    # annotation should not match, but the top-level EXISTS subquery is not
    # correctly scoped to the sample, so both rows are returned.
    assert len(results) == 2


def test_to_match_expression__classification_label_at_top_level(
    db_session: Session,
) -> None:
    """classification.label at the top level without ClassificationMatchExpr.

    The ForeignComparableField generates an EXISTS through .has(), so the
    query executes without error.  However, it matches *any* annotation whose
    label equals the value, regardless of annotation type.
    """
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    image = create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/img.jpg")
    # Second sample has no annotations at all.
    create_image(session=db_session, collection_id=cid, file_path_abs="/path/to/bare.jpg")
    label = create_annotation_label(session=db_session, root_collection_id=cid, label_name="cat")
    # Create an OBJECT_DETECTION annotation with label "cat".
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_data={"x": 0, "y": 0, "width": 10, "height": 10},
    )

    # Ask for classification.label == "cat" at the top level.
    expr = StringExpr(
        field=FieldRef(table="classification", name="label"),
        operator=EqualityComparisonOperator.EQ,
        value="cat",
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    # Wrong: both samples match (2 instead of 0).  The bare sample has no
    # annotations at all, yet it matches because the top-level EXISTS
    # subquery is not scoped to the sample.  The annotated sample matches
    # because the subquery ignores annotation_type.
    assert len(results) == 2
