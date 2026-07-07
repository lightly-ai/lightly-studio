"""SampleFilter class."""

from typing import Literal, Optional
from uuid import UUID

import sqlalchemy
from pydantic import BaseModel, PrivateAttr
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.embedding_region import EmbeddingRegion
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_confusion_matrix import ConfusionCell
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.metadata_resolver import metadata_filter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.type_definitions import QueryType


class SampleFilter(BaseModel):
    """Encapsulates filter parameters for querying samples."""

    filter_type: Literal["sample"] = "sample"
    tag_ids: Optional[list[UUID]] = None
    metadata_filters: Optional[list[MetadataFilter]] = None
    sample_ids: Optional[list[UUID]] = None
    has_captions: Optional[bool] = None
    annotations_filter: Optional[AnnotationsFilter] = None
    confusion_cell: Optional[ConfusionCell] = None
    # Lasso/rectangle selection from the embedding plot, sent as geometry rather than an explicit
    # id list (see LIG-9903). Resolved to concrete sample ids by ``resolve_embedding_region``
    # before the filter is applied, since the point-in-polygon test needs a database session that
    # ``apply`` does not have access to.
    embedding_region: Optional[EmbeddingRegion] = None

    # Sample ids ``embedding_region`` resolves to, populated by ``resolve_embedding_region``.
    # ``None`` means "not resolved yet"; an empty list means the region encloses no points. Kept
    # private so it never enters the request/response schema (unlike a client-settable field).
    _region_sample_ids: Optional[list[UUID]] = PrivateAttr(default=None)

    # Query expression filter
    #
    # Adds an arbitrary "where" condition that can be expressed with QueryExpr.
    #
    # Important note: The expression can (and usually will) reference fields outside of SampleTable.
    # It is caller's responsibility to ensure that the necessary joins are present in the query
    # before applying this filter.
    query_expr: Optional[QueryExpr] = None

    def resolve_embedding_region(self, session: Session, collection_id: UUID) -> None:
        """Resolve ``embedding_region`` to concrete sample ids, stored on the filter.

        Must be called before ``apply`` whenever a region is set: the point-in-polygon test needs a
        database session that ``apply`` does not have access to. No-op when no region is set.
        """
        if self.embedding_region is None:
            return
        # Imported locally to break a cycle: embedding_region_resolver -> twodim_embedding_resolver
        # -> sample_embedding_resolver -> sample_filter (this module).
        from lightly_studio.resolvers import embedding_region_resolver  # noqa: PLC0415

        self._region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=self.embedding_region,
        )

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        query = self._apply_sample_ids_filter(query)
        query = self._apply_embedding_region_filter(query)
        query = self._apply_annotation_filters(query)
        query = self._apply_tag_filters(query)
        query = self._apply_confusion_cell_filter(query)
        query = self._apply_metadata_filters(query)
        query = self._apply_captions_filter(query)
        return self._apply_query_expr_filter(query)

    def _apply_sample_ids_filter(self, query: QueryType) -> QueryType:
        if self.sample_ids:
            return query.where(
                db_array.in_array(column=col(SampleTable.sample_id), values=self.sample_ids)
            )
        return query

    def _apply_embedding_region_filter(self, query: QueryType) -> QueryType:
        if self.embedding_region is None:
            return query
        if self._region_sample_ids is None:
            raise RuntimeError(
                "embedding_region must be resolved with resolve_embedding_region() before apply()."
            )
        # An empty region encloses no points and must match nothing (not everything).
        if not self._region_sample_ids:
            return query.where(sqlalchemy.false())
        return query.where(
            db_array.in_array(column=col(SampleTable.sample_id), values=self._region_sample_ids)
        )

    def _apply_annotation_filters(self, query: QueryType) -> QueryType:
        if self.annotations_filter is None:
            return query
        return self.annotations_filter.apply_to_parent_sample_query(
            query=query,
            sample_id_column=col(SampleTable.sample_id),
        )

    def _apply_tag_filters(self, query: QueryType) -> QueryType:
        if not self.tag_ids:
            return query

        sample_ids_subquery = (
            select(SampleTable.sample_id)
            .join(SampleTable.tags)
            .where(db_array.in_array(column=col(TagTable.tag_id), values=self.tag_ids))
            .distinct()
        )
        return query.where(col(SampleTable.sample_id).in_(sample_ids_subquery))

    def _apply_confusion_cell_filter(self, query: QueryType) -> QueryType:
        if self.confusion_cell is None:
            return query
        sample_ids_subquery = self._build_confusion_cell_subquery(self.confusion_cell)
        return query.where(col(SampleTable.sample_id).in_(sample_ids_subquery))

    def _build_confusion_cell_subquery(self, confusion_cell: ConfusionCell) -> SelectOfScalar[UUID]:
        # Resolve the cell to its samples with a subquery against the persisted
        # pairing metrics, joining annotation labels by name (unique per dataset),
        # mirroring the tag-filter subquery pattern. Each side is handled
        # independently: a real label inner-joins its annotation/label and matches by
        # name; a null label (synthetic margin bucket) instead requires that side's
        # annotation id to be NULL (false positive when gt is null, false negative
        # when pred is null). The model rejects the both-null combination upstream.
        gt_annotation = aliased(AnnotationBaseTable)
        pred_annotation = aliased(AnnotationBaseTable)
        gt_label = aliased(AnnotationLabelTable)
        pred_label = aliased(AnnotationLabelTable)

        subquery = select(EvaluationAnnotationMetricTable.sample_id).where(
            col(EvaluationAnnotationMetricTable.evaluation_run_id)
            == confusion_cell.evaluation_run_id
        )

        if confusion_cell.gt_label is not None:
            subquery = (
                subquery.join(
                    gt_annotation,
                    col(EvaluationAnnotationMetricTable.gt_annotation_id)
                    == col(gt_annotation.sample_id),
                )
                .join(
                    gt_label,
                    col(gt_annotation.annotation_label_id) == col(gt_label.annotation_label_id),
                )
                .where(col(gt_label.annotation_label_name) == confusion_cell.gt_label)
            )
        else:
            subquery = subquery.where(
                col(EvaluationAnnotationMetricTable.gt_annotation_id).is_(None)
            )

        if confusion_cell.pred_label is not None:
            subquery = (
                subquery.join(
                    pred_annotation,
                    col(EvaluationAnnotationMetricTable.pred_annotation_id)
                    == col(pred_annotation.sample_id),
                )
                .join(
                    pred_label,
                    col(pred_annotation.annotation_label_id) == col(pred_label.annotation_label_id),
                )
                .where(col(pred_label.annotation_label_name) == confusion_cell.pred_label)
            )
        else:
            subquery = subquery.where(
                col(EvaluationAnnotationMetricTable.pred_annotation_id).is_(None)
            )

        return subquery.distinct()

    def _apply_metadata_filters(self, query: QueryType) -> QueryType:
        if self.metadata_filters:
            return metadata_filter.apply_metadata_filters(
                query,
                self.metadata_filters,
                metadata_model=SampleMetadataTable,
                metadata_join_condition=SampleMetadataTable.sample_id == SampleTable.sample_id,
            )
        return query

    def _apply_captions_filter(self, query: QueryType) -> QueryType:
        if self.has_captions is None:
            return query
        if self.has_captions:
            return query.where(col(SampleTable.captions).any())
        return query.where(~col(SampleTable.captions).any())

    def _apply_query_expr_filter(self, query: QueryType) -> QueryType:
        if self.query_expr is None:
            return query
        match_expression = query_translation.to_match_expression(self.query_expr.match_expr)
        return query.where(match_expression.get())
