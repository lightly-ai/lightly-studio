from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlmodel import Session, select

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.query_language import (
    AndExpr,
    ClassificationMatchExpr,
    DatetimeExpr,
    EqualityComparisonOperator,
    FieldRef,
    IntegerExpr,
    NotExpr,
    OrdinalComparisonOperator,
    OrExpr,
    QueryExpr,
    StringExpr,
    TagsContainsExpr,
    to_match_expression,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def test_query_tree_accepts_valid_image_and_annotation_nodes() -> None:
    tree = QueryExpr.model_validate(
        {
            "root": {
                "type": "and",
                "children": [
                    {
                        "type": "integer_expr",
                        "field": {"table": "image", "name": "width"},
                        "operator": ">=",
                        "value": 128,
                    },
                    {
                        "type": "classification_match_expr",
                        "subexpr": {
                            "type": "string_expr",
                            "field": {"table": "classification", "name": "label"},
                            "operator": "==",
                            "value": "cat",
                        },
                    },
                ],
            }
        }
    )

    assert isinstance(tree.root, AndExpr)


def test_query_tree_rejects_wrong_value_type_for_image_width() -> None:
    with pytest.raises(ValidationError):
        QueryExpr.model_validate(
            {
                "root": {
                    "type": "integer_expr",
                    "field": {"table": "image", "name": "width"},
                    "operator": "==",
                    "value": "123",
                }
            }
        )


def test_query_tree_rejects_wrong_operator_for_video_duration() -> None:
    with pytest.raises(ValidationError):
        QueryExpr.model_validate(
            {
                "root": {
                    "type": "equality_float_expr",
                    "field": {"table": "video", "name": "duration_s"},
                    "operator": ">=",
                    "value": 3.5,
                }
            }
        )


def test_query_tree_rejects_numeric_classification_criteria() -> None:
    with pytest.raises(ValidationError):
        QueryExpr.model_validate(
            {
                "root": {
                    "type": "classification_match_expr",
                    "subexpr": {
                        "type": "integer_expr",
                        "field": {"table": "object_detection", "name": "width"},
                        "operator": ">=",
                        "value": 0.5,
                    },
                }
            }
        )


def test_query_tree_parses_image_datetime_values() -> None:
    tree = QueryExpr.model_validate(
        {
            "root": {
                "type": "datetime_expr",
                "field": {"table": "image", "name": "created_at"},
                "operator": ">=",
                "value": "2026-01-01T00:00:00Z",
            }
        }
    )

    assert isinstance(tree.root, DatetimeExpr)
    assert tree.root.value == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_query_tree_constructed_from_pydantic_classes() -> None:
    tree = QueryExpr(
        root=AndExpr(
            children=[
                IntegerExpr(
                    field=FieldRef(table="image", name="width"),
                    operator=OrdinalComparisonOperator.GTE,
                    value=128,
                ),
                OrExpr(
                    children=[
                        TagsContainsExpr(
                            field=FieldRef(table="image", name="tags"),
                            tag_name="reviewed",
                        ),
                        NotExpr(
                            child=StringExpr(
                                field=FieldRef(table="image", name="file_name"),
                                operator=EqualityComparisonOperator.EQ,
                                value="skip.jpg",
                            ),
                        ),
                    ],
                ),
                ClassificationMatchExpr(
                    subexpr=StringExpr(
                        field=FieldRef(table="classification", name="label"),
                        operator=EqualityComparisonOperator.EQ,
                        value="cat",
                    ),
                ),
            ],
        ),
    )

    assert isinstance(tree.root, AndExpr)
    assert len(tree.root.children) == 3
    assert tree.model_dump()["root"]["type"] == "and"


def test_to_match_expression_compiles_nested_boolean_tree_to_sql() -> None:
    tree = QueryExpr.model_validate(
        {
            "root": {
                "type": "and",
                "children": [
                    {
                        "type": "integer_expr",
                        "field": {"table": "image", "name": "width"},
                        "operator": ">=",
                        "value": 128,
                    },
                    {
                        "type": "or",
                        "children": [
                            {
                                "type": "tags_contains_expr",
                                "field": {"table": "image", "name": "tags"},
                                "tag_name": "reviewed",
                            },
                            {
                                "type": "not",
                                "child": {
                                    "type": "string_expr",
                                    "field": {"table": "image", "name": "file_name"},
                                    "operator": "==",
                                    "value": "skip.jpg",
                                },
                            },
                        ],
                    },
                ],
            }
        }
    )

    query = select(ImageTable).where(to_match_expression(tree.root).get())
    sql = str(query.compile(compile_kwargs={"literal_binds": True}))

    assert "image.width >= 128" in sql
    assert "EXISTS (SELECT 1" in sql
    assert "tag.name = 'reviewed'" in sql
    assert "image.file_name != 'skip.jpg'" in sql


def test_to_match_expression_compiles_object_detection_query_to_sql() -> None:
    tree = QueryExpr.model_validate(
        {
            "root": {
                "type": "object_detection_match_expr",
                "subexpr": {
                    "type": "and",
                    "children": [
                        {
                            "type": "string_expr",
                            "field": {"table": "object_detection", "name": "label"},
                            "operator": "==",
                            "value": "cat",
                        },
                        {
                            "type": "integer_expr",
                            "field": {"table": "object_detection", "name": "width"},
                            "operator": ">",
                            "value": 100,
                        },
                    ],
                },
            }
        }
    )

    query = select(ImageTable).where(to_match_expression(tree.root).get())
    sql = str(query.compile(compile_kwargs={"literal_binds": True}))

    assert "annotation_type = 'OBJECT_DETECTION'" in sql
    assert "annotation_label.annotation_label_name = 'cat'" in sql
    assert "object_detection_annotation.width > 100" in sql


def test_to_match_expression_compiles_video_query_to_sql() -> None:
    tree = QueryExpr.model_validate(
        {
            "root": {
                "type": "and",
                "children": [
                    {
                        "type": "string_expr",
                        "field": {"table": "video", "name": "file_name"},
                        "operator": "==",
                        "value": "clip.mp4",
                    },
                    {
                        "type": "ordinal_float_expr",
                        "field": {"table": "video", "name": "fps"},
                        "operator": ">=",
                        "value": 24,
                    },
                ],
            }
        }
    )

    sql = str(
        to_match_expression(tree.root).get().compile(compile_kwargs={"literal_binds": True})
    )

    assert "video.file_name = 'clip.mp4'" in sql
    assert "video.fps >= 24" in sql


def test_to_match_expression_filters_matching_samples(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    image1 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/1.jpg", width=160
    )
    image2 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/2.jpg", width=120
    )
    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )

    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image1.sample_id,
        annotation_label_id=label_cat.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image2.sample_id,
        annotation_label_id=label_dog.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )

    tree = QueryExpr.model_validate(
        {
            "root": {
                "type": "and",
                "children": [
                    {
                        "type": "integer_expr",
                        "field": {"table": "image", "name": "width"},
                        "operator": ">=",
                        "value": 128,
                    },
                    {
                        "type": "classification_match_expr",
                        "subexpr": {
                            "type": "string_expr",
                            "field": {"table": "classification", "name": "label"},
                            "operator": "==",
                            "value": "cat",
                        },
                    },
                ],
            }
        }
    )

    query = (
        select(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
        .where(to_match_expression(tree.root).get())
    )
    results = db_session.exec(query).all()

    assert [image.sample_id for image in results] == [image1.sample_id]
