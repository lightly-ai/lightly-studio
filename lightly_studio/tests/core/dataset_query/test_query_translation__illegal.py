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
    wide_image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/wide.jpg", width=800
    )
    narrow_image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/narrow.jpg", width=200
    )
    label = create_annotation_label(session=db_session, root_collection_id=cid, label_name="cat")
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=wide_image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=narrow_image.sample_id,
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

    # Wrong: both samples have the same classification annotation shape, but
    # only the wide image matches because image.width is resolved from the
    # outer image row inside the classification subquery.
    assert [result.sample_id for result in results] == [wide_image.sample_id]


def test_to_match_expression__classification_field_inside_object_detection_matcher(
    db_session: Session,
) -> None:
    """classification.label inside ObjectDetectionMatchExpr mixes annotation contexts.

    The label lookup goes through AnnotationBaseTable.annotation_label
    regardless of the field's declared context. Wrapped in
    ObjectDetectionMatchExpr, the same label predicate is silently evaluated
    against object-detection annotations instead of classification ones.
    """
    dataset = create_collection(session=db_session)
    cid = dataset.collection_id
    classification_image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/classification.jpg"
    )
    object_detection_image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/object_detection.jpg"
    )
    other_detection_image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/other_detection.jpg"
    )
    dog_label = create_annotation_label(
        session=db_session, root_collection_id=cid, label_name="dog"
    )
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=cid, label_name="cat"
    )

    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=classification_image.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=object_detection_image.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_data={"x": 0, "y": 0, "width": 10, "height": 10},
    )
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=other_detection_image.sample_id,
        annotation_label_id=cat_label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_data={"x": 0, "y": 0, "width": 10, "height": 10},
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

    # Wrong: the field says "classification.label", but the matcher's
    # annotation_type filter makes it behave like a generic label predicate on
    # object detections. The object-detection sample matches, while the actual
    # classification sample does not.
    assert [result.sample_id for result in results] == [object_detection_image.sample_id]


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
    object_detection_image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/object_detection.jpg"
    )
    classification_other_label_image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/classification_other.jpg"
    )
    bare_image = create_image(
        session=db_session, collection_id=cid, file_path_abs="/path/to/bare.jpg"
    )
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=cid, label_name="cat"
    )
    dog_label = create_annotation_label(
        session=db_session, root_collection_id=cid, label_name="dog"
    )
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=object_detection_image.sample_id,
        annotation_label_id=cat_label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_data={"x": 0, "y": 0, "width": 10, "height": 10},
    )
    create_annotation(
        session=db_session,
        collection_id=cid,
        sample_id=classification_other_label_image.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    expr = StringExpr(
        field=FieldRef(table="classification", name="label"),
        operator=EqualityComparisonOperator.EQ,
        value="cat",
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    # Wrong: the top-level EXISTS subquery is not scoped to the current sample,
    # and the predicate ignores annotation_type. A single object-detection
    # annotation labeled "cat" makes every sample match.
    assert {result.sample_id for result in results} == {
        object_detection_image.sample_id,
        classification_other_label_image.sample_id,
        bare_image.sample_id,
    }
