"""Query evaluation matches (TP/FP/FN annotation pairings) with crop payload."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import case
from sqlalchemy.orm import aliased
from sqlmodel import Session, and_, col, func, or_, select
from sqlmodel.sql.expression import Select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationView,
    ImageAnnotationView,
    SampleAnnotationView,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricTable,
    EvaluationMatchesWithCountView,
    EvaluationMatchSortField,
    EvaluationMatchType,
    EvaluationMatchView,
)
from lightly_studio.models.evaluation_confusion_matrix import ConfusionCell
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.resolvers.image_filter import ImageFilter

# Object detection stores the pairing IoU under this metric name; FP/FN rows have
# no metric. Restricting to these keeps exactly one row per match.
_IOU_METRIC_NAME = "iou"

# The rows selected by the matches query: one metric row joined to its (optional)
# ground-truth and prediction annotations and the parent image.
_MatchesQuery = Select[
    tuple[EvaluationAnnotationMetricTable, AnnotationBaseTable, AnnotationBaseTable, ImageTable]
]


def _apply_confusion_cell_filter(
    query: _MatchesQuery,
    confusion_cell: ConfusionCell,
    gt_annotation: type[AnnotationBaseTable],
    pred_annotation: type[AnnotationBaseTable],
) -> _MatchesQuery:
    """Keep only the metric rows in the confusion cell's gt/pred label pairing.

    A real label is matched by name against the joined annotation's label (names are
    unique per dataset); a null label is the synthetic margin bucket, requiring that
    side's annotation id to be NULL (false positive when gt is null, false negative
    when pred is null). The model rejects the both-null combination upstream.
    """
    if confusion_cell.gt_label is not None:
        query = query.where(
            col(gt_annotation.annotation_label_id).in_(
                select(AnnotationLabelTable.annotation_label_id).where(
                    col(AnnotationLabelTable.annotation_label_name) == confusion_cell.gt_label
                )
            )
        )
    else:
        query = query.where(col(EvaluationAnnotationMetricTable.gt_annotation_id).is_(None))

    if confusion_cell.pred_label is not None:
        query = query.where(
            col(pred_annotation.annotation_label_id).in_(
                select(AnnotationLabelTable.annotation_label_id).where(
                    col(AnnotationLabelTable.annotation_label_name) == confusion_cell.pred_label
                )
            )
        )
    else:
        query = query.where(col(EvaluationAnnotationMetricTable.pred_annotation_id).is_(None))

    return query


def get_matches_with_payload(  # noqa: PLR0913
    session: Session,
    evaluation_run_id: UUID,
    collection_id: UUID,
    match_types: list[EvaluationMatchType] | None = None,
    annotation_label_ids: list[UUID] | None = None,
    confusion_cell: ConfusionCell | None = None,
    image_filter: ImageFilter | None = None,
    sort_field: EvaluationMatchSortField = EvaluationMatchSortField.IOU,
    sort_direction: SortDirection = SortDirection.desc,
    pagination: Paginated | None = None,
) -> EvaluationMatchesWithCountView:
    """Return paginated evaluation matches enriched with their boxes and crop.

    Each row of ``evaluation_annotation_metric`` becomes one match. True positives
    carry both the ground-truth and prediction annotations plus their IoU; false
    positives carry only the prediction; false negatives only the ground truth.

    Args:
        session: Active database session.
        evaluation_run_id: Run whose pairings are listed.
        collection_id: Image collection used to scope image-level filters.
        match_types: Optional subset of TP/FP/FN to keep. ``None`` keeps all.
        annotation_label_ids: Optional labels; a match is kept when its ground
            truth OR prediction label is in the set (captures class confusion).
        confusion_cell: Optional confusion-matrix cell. Keeps only the matches in
            that exact ground-truth/prediction label pairing; a null label selects
            the false-positive (no ground truth) or false-negative (no prediction)
            margin bucket. The cell's own run id is ignored: the query is already
            scoped to ``evaluation_run_id``.
        image_filter: Optional image-level filter (tags, metadata, dimensions,
            sample ids) applied to the parent image of each match.
        sort_field: Primary ordering. ``iou`` (default) orders by IoU; ``confidence``
            orders by the prediction confidence. Rows missing the chosen value are
            always pushed to the end.
        sort_direction: Direction applied to the chosen sort field.
        pagination: Optional offset/limit pagination.

    Returns:
        Matches ordered by the requested field together with the total count and
        cursor. The default orders by descending IoU, leaving IoU-less matches
        (false positives and false negatives) at the end.
    """
    gt_annotation = aliased(AnnotationBaseTable)
    pred_annotation = aliased(AnnotationBaseTable)

    gt_id = col(EvaluationAnnotationMetricTable.gt_annotation_id)
    pred_id = col(EvaluationAnnotationMetricTable.pred_annotation_id)
    gt_set = gt_id.is_not(None)
    pred_set = pred_id.is_not(None)

    base_query = (
        select(
            EvaluationAnnotationMetricTable,
            gt_annotation,
            pred_annotation,
            ImageTable,
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(EvaluationAnnotationMetricTable.sample_id),
        )
        .join(
            gt_annotation,
            col(gt_annotation.sample_id) == col(EvaluationAnnotationMetricTable.gt_annotation_id),
            isouter=True,
        )
        .join(
            pred_annotation,
            col(pred_annotation.sample_id)
            == col(EvaluationAnnotationMetricTable.pred_annotation_id),
            isouter=True,
        )
        .where(col(EvaluationAnnotationMetricTable.evaluation_run_id) == evaluation_run_id)
        .where(
            or_(
                col(EvaluationAnnotationMetricTable.metric_name).is_(None),
                col(EvaluationAnnotationMetricTable.metric_name) == _IOU_METRIC_NAME,
            )
        )
    )

    if match_types:
        type_conditions = []
        if EvaluationMatchType.TP in match_types:
            type_conditions.append(and_(gt_set, pred_set))
        if EvaluationMatchType.FP in match_types:
            type_conditions.append(and_(pred_set, gt_id.is_(None)))
        if EvaluationMatchType.FN in match_types:
            type_conditions.append(and_(gt_set, pred_id.is_(None)))
        base_query = base_query.where(or_(*type_conditions))

    if annotation_label_ids:
        base_query = base_query.where(
            or_(
                col(gt_annotation.annotation_label_id).in_(annotation_label_ids),
                col(pred_annotation.annotation_label_id).in_(annotation_label_ids),
            )
        )

    if confusion_cell is not None:
        base_query = _apply_confusion_cell_filter(
            query=base_query,
            confusion_cell=confusion_cell,
            gt_annotation=gt_annotation,
            pred_annotation=pred_annotation,
        )

    if image_filter is not None:
        parent_sample_ids = image_filter.build_sample_ids_query(collection_id=collection_id)
        base_query = base_query.where(
            col(EvaluationAnnotationMetricTable.sample_id).in_(parent_sample_ids)
        )

    total_count = session.exec(select(func.count()).select_from(base_query.subquery())).one()

    # IoU lives on the metric row; confidence on the prediction annotation.
    sort_col = (
        col(pred_annotation.confidence)
        if sort_field == EvaluationMatchSortField.CONFIDENCE
        else col(EvaluationAnnotationMetricTable.value)
    )
    # Rows lacking the chosen value (FP/FN have no IoU; FN has no prediction, hence
    # no confidence) are kept at the end regardless of the requested direction.
    missing_last = case((sort_col.is_(None), 1), else_=0)
    sort_ordered = sort_col.asc() if sort_direction == SortDirection.asc else sort_col.desc()
    tiebreak = col(EvaluationAnnotationMetricTable.id).asc()
    ordered_query = base_query.order_by(missing_last, sort_ordered, tiebreak)

    if pagination is not None:
        ordered_query = ordered_query.offset(pagination.offset).limit(pagination.limit)

    next_cursor = None
    if pagination is not None and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    rows = session.exec(ordered_query).all()

    return EvaluationMatchesWithCountView(
        total_count=total_count,
        next_cursor=next_cursor,
        matches=[
            _build_match_view(metric=metric, gt=gt, pred=pred, image=image)
            for metric, gt, pred, image in rows
        ],
    )


def _build_match_view(
    metric: EvaluationAnnotationMetricTable,
    gt: AnnotationBaseTable | None,
    pred: AnnotationBaseTable | None,
    image: ImageTable,
) -> EvaluationMatchView:
    """Assemble a single match view from a metric row and its joined annotations."""
    if gt is not None and pred is not None:
        match_type = EvaluationMatchType.TP
    elif pred is not None:
        match_type = EvaluationMatchType.FP
    else:
        match_type = EvaluationMatchType.FN

    iou = metric.value if metric.metric_name == _IOU_METRIC_NAME else None

    return EvaluationMatchView(
        match_type=match_type,
        iou=iou,
        gt_annotation=AnnotationView.from_annotation_table(annotation=gt) if gt else None,
        pred_annotation=AnnotationView.from_annotation_table(annotation=pred) if pred else None,
        parent_sample_data=ImageAnnotationView(
            sample_id=image.sample_id,
            file_path_abs=image.file_path_abs,
            width=image.width,
            height=image.height,
            sample=SampleAnnotationView(collection_id=image.sample.collection_id),
        ),
    )
