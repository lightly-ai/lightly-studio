"""Convert dataset-query expressions to the query format that the transport sends.

Sample fields, tags, metadata, annotation queries, video event and frame queries, and
evaluation queries are supported. Other expressions raise `UnsupportedQueryError`, and the
caller uses the SQL path.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from lightly_studio.core.dataset_query import query_translation, video_query_validation
from lightly_studio.core.dataset_query.annotation_evaluation_metric_expression import (
    AnnotationEvaluationMetricMatchExpression,
)
from lightly_studio.core.dataset_query.annotation_evaluation_query import AnnotationMetricQuery
from lightly_studio.core.dataset_query.annotation_expression import (
    AnnotationSourceMatchExpression,
    RelationshipMatchExpression,
)
from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.classification_query import ClassificationQuery
from lightly_studio.core.dataset_query.evaluation_metric_expression import (
    EvaluationMetricMatchExpression,
)
from lightly_studio.core.dataset_query.field import Field
from lightly_studio.core.dataset_query.field_expression import (
    ComparableFieldExpression,
    OrdinalFieldExpression,
)
from lightly_studio.core.dataset_query.foreign_field import (
    ForeignComparableField,
    ForeignNumericalField,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.metadata_expression import MetadataComparisonExpression
from lightly_studio.core.dataset_query.object_detection_query import ObjectDetectionQuery
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.core.dataset_query.polygon_query import PolygonQuery
from lightly_studio.core.dataset_query.query_translation import FieldExpr
from lightly_studio.core.dataset_query.sample_evaluation_query import SampleEvaluationQuery
from lightly_studio.core.dataset_query.segmentation_mask_query import SegmentationMaskQuery
from lightly_studio.core.dataset_query.tags_expression import TagsContainsExpression
from lightly_studio.core.dataset_query.video_event_query import VideoEventQuery
from lightly_studio.core.dataset_query.video_frame_query import VideoFrameQuery
from lightly_studio.errors import QueryExprError
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    ConfusionMatchExpr,
    DatetimeExpr,
    EqualityComparisonOperator,
    EvaluationMetricAndExpr,
    EvaluationMetricComparisonExpr,
    EvaluationMetricNotExpr,
    EvaluationMetricOrExpr,
    FalseNegativeMatchExpr,
    FalsePositiveMatchExpr,
    FieldRef,
    MatchExpr,
    MetadataComparisonExpr,
    NotExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    OrExpr,
    PolygonMatchExpr,
    QueryExpr,
    SampleEvaluationMatchExpr,
    SampleEvaluationMetricExpr,
    SegmentationMaskMatchExpr,
    StringExpr,
    TagsContainsExpr,
    VideoEventMatchExpr,
    VideoFrameMatchExpr,
)
from lightly_studio.models.sample_query import SortKey
from lightly_studio.models.sort_direction import SortDirection

_ScopedQuery = (
    ClassificationQuery
    | ObjectDetectionQuery
    | SegmentationMaskQuery
    | PolygonQuery
    | VideoEventQuery
    | VideoFrameQuery
)
_ScopedMatchExpr = (
    ClassificationMatchExpr
    | ObjectDetectionMatchExpr
    | SegmentationMaskMatchExpr
    | PolygonMatchExpr
    | VideoEventMatchExpr
    | VideoFrameMatchExpr
)

# The criteria of these queries refer to the fields of the table.
_SCOPED_QUERIES: dict[type[_ScopedQuery], tuple[type[_ScopedMatchExpr], str]] = {
    ClassificationQuery: (ClassificationMatchExpr, "classification"),
    ObjectDetectionQuery: (ObjectDetectionMatchExpr, "object_detection"),
    SegmentationMaskQuery: (SegmentationMaskMatchExpr, "segmentation_mask"),
    PolygonQuery: (PolygonMatchExpr, "polygon"),
    VideoEventQuery: (VideoEventMatchExpr, "event"),
    VideoFrameQuery: (VideoFrameMatchExpr, "video_frame"),
}

# The relationships that each scope allows, with the table of the related fields.
_RELATIONSHIP_TABLES: dict[tuple[str, object], str] = {
    ("classification", AnnotationBaseTable.annotation_label): "classification",
    ("event", AnnotationBaseTable.annotation_label): "event",
    ("event", AnnotationBaseTable.temporal_span_details): "event",
    ("object_detection", AnnotationBaseTable.annotation_label): "object_detection",
    ("object_detection", AnnotationBaseTable.object_detection_details): "object_detection",
    ("segmentation_mask", AnnotationBaseTable.annotation_label): "segmentation_mask",
    ("segmentation_mask", AnnotationBaseTable.segmentation_details): "segmentation_mask",
    ("polygon", AnnotationBaseTable.annotation_label): "polygon",
    ("polygon", AnnotationBaseTable.polygon_details): "polygon",
}


class UnsupportedQueryError(NotImplementedError):
    """The transport cannot send this query yet."""


def to_query_expr(match_expression: MatchExpression, sample_type: SampleType) -> QueryExpr:
    """Convert a match expression on samples of the sample type to a `QueryExpr`.

    Raises:
        UnsupportedQueryError: If the expression uses a field that is not supported.
    """
    try:
        match_expr = _to_match_expr(expression=match_expression, scope=sample_type.value)
        video_query_validation.validate(expr=match_expr, scope=sample_type.value)
        return QueryExpr(match_expr=match_expr)
    except (ValidationError, QueryExprError) as error:
        raise UnsupportedQueryError(f"The filter is not supported: {error}") from error


def to_sort_keys(order_by: Sequence[OrderByExpression], sample_type: SampleType) -> list[SortKey]:
    """Convert order-by expressions on samples of the sample type to sort keys.

    Raises:
        UnsupportedQueryError: If a sort is not on a sample field.
    """
    keys = []
    for expression in order_by:
        if not isinstance(expression, OrderByField):
            raise UnsupportedQueryError(f"The sort {type(expression).__name__} is not supported.")
        direction = SortDirection.asc if expression.ascending else SortDirection.desc
        field_ref, _ = _lookup_field(field=expression.field, scope=sample_type.value)
        keys.append(SortKey(field=field_ref, direction=direction))
    return keys


def _to_match_expr(expression: MatchExpression, scope: str) -> MatchExpr:
    if isinstance(expression, AND):
        return AndExpr(
            children=[_to_match_expr(expression=term, scope=scope) for term in expression.terms]
        )
    if isinstance(expression, OR):
        return OrExpr(
            children=[_to_match_expr(expression=term, scope=scope) for term in expression.terms]
        )
    if isinstance(expression, NOT):
        return NotExpr(child=_to_match_expr(expression=expression.term, scope=scope))
    if isinstance(expression, _ScopedQuery):
        return _to_scoped_match_expr(query=expression)
    if isinstance(expression, RelationshipMatchExpression):
        relationship = expression.relationship
        if (scope, relationship) not in _RELATIONSHIP_TABLES:
            raise UnsupportedQueryError(
                f"The relationship {relationship} of {scope} is not supported."
            )
        table = _RELATIONSHIP_TABLES[(scope, relationship)]
        return _to_match_expr(expression=expression.criterion, scope=table)
    return _to_leaf_expr(expression=expression, scope=scope)


def _to_scoped_match_expr(query: _ScopedQuery) -> MatchExpr:
    expr_type, scope = _SCOPED_QUERIES[type(query)]
    subexpr = _to_subexpr(criterion=query.criterion, scope=scope)
    return expr_type.model_validate({"subexpr": subexpr})


def _to_subexpr(criterion: MatchExpression, scope: str) -> MatchExpr | None:
    """Convert the criteria of a scoped query. None means that the query has no criteria."""
    terms = criterion.terms if isinstance(criterion, AND) else (criterion,)
    if not terms:
        return None
    if len(terms) == 1:
        return _to_match_expr(expression=terms[0], scope=scope)
    return AndExpr(children=[_to_match_expr(expression=term, scope=scope) for term in terms])


def _to_leaf_expr(expression: MatchExpression, scope: str) -> MatchExpr:
    if isinstance(expression, TagsContainsExpression):
        if not query_translation.has_tags(table=scope):
            raise UnsupportedQueryError(f"Tags of {scope} are not supported.")
        tags = FieldRef(table=scope, name="tags")
        return TagsContainsExpr(field=tags, tag_name=expression.tag_name)
    if isinstance(expression, MetadataComparisonExpression):
        operator = OrdinalComparisonOperator(expression.comparison)
        return MetadataComparisonExpr(
            path=expression.path, operator=operator, value=expression.value
        )
    if isinstance(expression, (ComparableFieldExpression, OrdinalFieldExpression)):
        field_ref, expr_type = _lookup_field(field=expression.field, scope=scope)
        _check_field_value(value=expression.value, expr_type=expr_type)
        return expr_type.model_validate(
            {"field": field_ref, "operator": expression.operator, "value": expression.value}
        )
    if isinstance(expression, AnnotationSourceMatchExpression):
        if not query_translation.has_annotation_source(table=scope):
            raise UnsupportedQueryError(f"Annotation sources of {scope} are not supported.")
        source = FieldRef(table=scope, name="source")
        equality = (
            EqualityComparisonOperator.NEQ if expression.negate else EqualityComparisonOperator.EQ
        )
        return StringExpr(field=source, operator=equality, value=expression.source_name)
    if isinstance(expression, (SampleEvaluationQuery, AnnotationMetricQuery)):
        return _to_evaluation_expr(query=expression)
    raise UnsupportedQueryError(f"The filter {type(expression).__name__} is not supported.")


def _check_field_value(value: object, expr_type: type[FieldExpr]) -> None:
    # Pydantic coerces other values to a datetime.
    if expr_type is DatetimeExpr and not isinstance(value, datetime):
        raise UnsupportedQueryError(f"The value {value!r} is not a datetime.")


def _to_evaluation_expr(query: SampleEvaluationQuery | AnnotationMetricQuery) -> MatchExpr:
    if isinstance(query, AnnotationMetricQuery):
        return _to_annotation_metric_expr(query=query)
    return SampleEvaluationMatchExpr(
        run_name=query.run_name,
        criteria=[_to_sample_metric_expr(expression=term) for term in query.criteria],
    )


def _to_sample_metric_expr(expression: MatchExpression) -> SampleEvaluationMetricExpr:
    if isinstance(expression, AND):
        return EvaluationMetricAndExpr(
            children=[_to_sample_metric_expr(expression=term) for term in expression.terms]
        )
    if isinstance(expression, OR):
        return EvaluationMetricOrExpr(
            children=[_to_sample_metric_expr(expression=term) for term in expression.terms]
        )
    if isinstance(expression, NOT):
        return EvaluationMetricNotExpr(child=_to_sample_metric_expr(expression=expression.term))
    if isinstance(expression, EvaluationMetricMatchExpression):
        return _to_metric_comparison_expr(metric=expression)
    raise UnsupportedQueryError(
        f"The sample evaluation criterion {type(expression).__name__} is not supported."
    )


def _to_annotation_metric_expr(query: AnnotationMetricQuery) -> MatchExpr:
    """Convert the query states that the `AnnotationMetricQuery` class methods create."""
    ground_truth, prediction = query.gt_label_name, query.pred_label_name
    if query.match_kind == "confusion" and ground_truth is not None and prediction is not None:
        return ConfusionMatchExpr(
            run_name=query.run_name,
            ground_truth=ground_truth,
            prediction=prediction,
            criteria=[_to_annotation_metric_criterion(criterion=term) for term in query.criteria],
        )
    if query.criteria:
        raise UnsupportedQueryError("Only confusion queries support metric criteria.")
    if query.match_kind == "false_positive" and ground_truth is None and prediction is not None:
        return FalsePositiveMatchExpr(run_name=query.run_name, prediction=prediction)
    if query.match_kind == "false_negative" and ground_truth is not None and prediction is None:
        return FalseNegativeMatchExpr(run_name=query.run_name, ground_truth=ground_truth)
    raise UnsupportedQueryError(
        f"The {query.match_kind} query with these class names is not supported."
    )


def _to_annotation_metric_criterion(criterion: MatchExpression) -> EvaluationMetricComparisonExpr:
    if not isinstance(criterion, AnnotationEvaluationMetricMatchExpression):
        raise UnsupportedQueryError(
            f"The annotation metric criterion {type(criterion).__name__} is not supported."
        )
    return _to_metric_comparison_expr(metric=criterion)


def _to_metric_comparison_expr(
    metric: EvaluationMetricMatchExpression | AnnotationEvaluationMetricMatchExpression,
) -> EvaluationMetricComparisonExpr:
    return EvaluationMetricComparisonExpr(
        metric_name=metric.metric_name,
        operator=OrdinalComparisonOperator(metric.operator),
        value=metric.value,
    )


def _lookup_field(field: Field, scope: str) -> tuple[FieldRef, type[FieldExpr]]:
    fields_by_column = _fields_by_column()
    key = (scope, field.get_sqlmodel_field())
    if key not in fields_by_column:
        raise UnsupportedQueryError(f"The field {type(field).__name__} is not supported.")
    return fields_by_column[key]


@functools.cache
def _fields_by_column() -> dict[tuple[str, Any], tuple[FieldRef, type[FieldExpr]]]:
    """Map (table, column) to the field reference and the expression type of the field."""
    fields_by_column: dict[tuple[str, Any], tuple[FieldRef, type[FieldExpr]]] = {}
    for expr_type, fields in query_translation.field_tables():
        for (table, name), field in fields.items():
            column = _column_of(field=field)
            if column is not None:
                key = (table, column)
                # The first table of a column wins.
                fields_by_column.setdefault(key, (FieldRef(table=table, name=name), expr_type))
    return fields_by_column


def _column_of(field: object) -> Any | None:
    if isinstance(field, (ForeignComparableField, ForeignNumericalField)):
        return field.field.get_sqlmodel_field()
    if isinstance(field, Field):
        return field.get_sqlmodel_field()
    return None
