"""Resolver functions for exporting collection samples based on filters."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import false
from sqlmodel import Session, and_, col, func, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.dataset_resolver.get_hierarchy import get_hierarchy
from lightly_studio.resolvers.image_filter import ImageFilter


class ExportFilter(BaseModel):
    """Export Filter to be used for including or excluding."""

    tag_ids: list[UUID] | None = Field(default=None, min_length=1, description="List of tag UUIDs")
    sample_ids: list[UUID] | None = Field(
        default=None, min_length=1, description="List of sample UUIDs"
    )
    annotation_ids: list[UUID] | None = Field(
        default=None, min_length=1, description="List of annotation UUIDs"
    )

    @model_validator(mode="after")
    def check_exactly_one(self) -> ExportFilter:  # noqa: N804
        """Ensure that exactly one of the fields is set."""
        count = (
            (self.tag_ids is not None)
            + (self.sample_ids is not None)
            + (self.annotation_ids is not None)
        )
        if count != 1:
            raise ValueError("Either tag_ids, sample_ids, or annotation_ids must be set.")
        return self


# TODO(Michal, 10/2025): Consider moving the export logic to a separate service.
# This is a legacy code from the initial implementation of the export feature.
def export(
    session: Session,
    collection_id: UUID,
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
    collection_filter: ImageFilter | None = None,
) -> list[str]:
    # TODO(lukas, 03/2026): take dataset_id instead of collection_id
    """Retrieve samples for exporting from a collection.

    Only one of include or exclude should be set and not both.
    Furthermore, the include and exclude filter can only have
    one type (tag_ids, sample_ids or annotations_ids) set.

    Args:
        session: SQLAlchemy session.
        collection_id: UUID of the collection.
        include: Filter to include samples.
        exclude: Filter to exclude samples.
        collection_filter: Active view filter applied on top of include/exclude.

    Returns:
        List of file paths
    """
    # Resolve any embedding-plot region selection to concrete sample ids before the query is
    # built (the point-in-polygon test needs the session, which `_build_export_query` lacks).
    sample_filter = collection_filter.sample_filter if collection_filter is not None else None
    if sample_filter is not None and sample_filter.embedding_region is not None:
        sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=sample_filter.embedding_region,
        )
    # Get all child collection IDs that could contain annotations
    annotation_collection_ids = _get_annotation_collection_ids(
        session=session, collection_id=collection_id
    )
    query = _build_export_query(
        collection_id=collection_id,
        annotation_collection_ids=annotation_collection_ids,
        include=include,
        exclude=exclude,
        collection_filter=collection_filter,
    )
    result = session.exec(query).all()
    return [sample.file_path_abs for sample in result]


def get_filtered_samples_count(
    session: Session,
    collection_id: UUID,
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
    collection_filter: ImageFilter | None = None,
) -> int:
    # TODO(lukas, 03/2026): take dataset_id instead of collection_id
    """Get statistics about the export query.

    Only one of include or exclude should be set and not both.
    Furthermore, the include and exclude filter can only have
    one type (tag_ids, sample_ids or annotations_ids) set.

    Args:
        session: SQLAlchemy session.
        collection_id: UUID of the collection.
        include: Filter to include samples.
        exclude: Filter to exclude samples.
        collection_filter: Active view filter applied on top of include/exclude.

    Returns:
        Count of files to be exported
    """
    # Resolve any embedding-plot region selection to concrete sample ids before the query is
    # built (the point-in-polygon test needs the session, which `_build_export_query` lacks).
    sample_filter = collection_filter.sample_filter if collection_filter is not None else None
    if sample_filter is not None and sample_filter.embedding_region is not None:
        sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=sample_filter.embedding_region,
        )
    # Get all child collection IDs that could contain annotations
    annotation_collection_ids = _get_annotation_collection_ids(
        session=session, collection_id=collection_id
    )
    query = _build_export_query(
        collection_id=collection_id,
        annotation_collection_ids=annotation_collection_ids,
        include=include,
        exclude=exclude,
        collection_filter=collection_filter,
    )
    count_query = select(func.count()).select_from(query.subquery())
    return session.exec(count_query).one() or 0


def _get_annotation_collection_ids(session: Session, collection_id: UUID) -> list[UUID]:
    # TODO(lukas, 03/2026): take dataset_id instead of collection_id, it's what we pass to
    # get_hierarchy()
    """Get all child collection IDs that could contain annotations.

    This includes the collection itself and all its child collections (recursively)
    that have sample_type ANNOTATION.

    Args:
        session: SQLAlchemy session.
        collection_id: UUID of the root collection.

    Returns:
        List of collection IDs that could contain annotations.
    """
    collection = session.get(CollectionTable, collection_id)
    if collection is None:
        raise ValueError(f"Collection with ID {collection_id} not found.")

    hierarchy = get_hierarchy(session, dataset_id=collection.dataset_id)
    return [col.collection_id for col in hierarchy if col.sample_type == SampleType.ANNOTATION]


def _build_export_query(  # noqa: C901
    collection_id: UUID,
    annotation_collection_ids: list[UUID],
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
    collection_filter: ImageFilter | None = None,
) -> SelectOfScalar[ImageTable]:
    """Build the export query based on filters.

    Args:
        collection_id: UUID of the collection.
        annotation_collection_ids: List of collection IDs that could contain annotations.
        include: Filter to include samples.
        exclude: Filter to exclude samples.
        collection_filter: Active view filter applied on top of include/exclude as an intersection.

    Returns:
        SQLModel select query
    """
    if not include and not exclude:
        raise ValueError("Include or exclude filter is required.")
    if include and exclude:
        raise ValueError("Cannot include and exclude at the same time.")

    active_view_subquery = (
        collection_filter.build_sample_ids_query(collection_id)
        if collection_filter is not None
        else None
    )

    # include tags or sample_ids or annotation_ids from result
    if include:
        if include.tag_ids:
            # Subquery: find parent_sample_ids that have annotations with matching tags
            annotation_tag_subquery = (
                select(AnnotationBaseTable.parent_sample_id)
                .join(SampleTable, col(AnnotationBaseTable.sample_id) == col(SampleTable.sample_id))
                .where(
                    col(SampleTable.tags).any(
                        and_(
                            TagTable.kind == "annotation",
                            db_array.in_array(column=col(TagTable.tag_id), values=include.tag_ids),
                        )
                    )
                )
            )

            query = (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(
                    or_(
                        # Samples with matching sample tags
                        col(SampleTable.tags).any(
                            and_(
                                TagTable.kind == "sample",
                                db_array.in_array(
                                    column=col(TagTable.tag_id), values=include.tag_ids
                                ),
                            )
                        ),
                        # Samples with matching annotation tags (via annotation sample)
                        col(SampleTable.sample_id).in_(annotation_tag_subquery),
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

        # get samples by specific sample_ids
        elif include.sample_ids:
            query = (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(
                    db_array.in_array(column=col(ImageTable.sample_id), values=include.sample_ids)
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

        # get samples by specific annotation_ids
        elif include.annotation_ids:
            # Annotations are stored in child collections, so filter by all annotation collection
            # IDs
            # Filter by checking if the annotation's sample_id belongs to a sample in
            # annotation_collection_ids
            annotation_sample_subquery = select(SampleTable.sample_id).where(
                db_array.in_array(
                    column=col(SampleTable.collection_id),
                    values=annotation_collection_ids,
                )
                if annotation_collection_ids
                else false()
            )
            query = (
                select(ImageTable)
                .join(ImageTable.sample)
                .join(SampleTable.annotations)
                .where(col(AnnotationBaseTable.sample_id).in_(annotation_sample_subquery))
                .where(
                    db_array.in_array(
                        column=col(AnnotationBaseTable.sample_id),
                        values=include.annotation_ids,
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

    # exclude tags or sample_ids or annotation_ids from result
    elif exclude:
        if exclude.tag_ids:
            # Subquery: find parent_sample_ids that have annotations with matching tags
            annotation_tag_subquery = (
                select(AnnotationBaseTable.parent_sample_id)
                .join(SampleTable, col(AnnotationBaseTable.sample_id) == col(SampleTable.sample_id))
                .where(
                    col(SampleTable.tags).any(
                        and_(
                            TagTable.kind == "annotation",
                            db_array.in_array(column=col(TagTable.tag_id), values=exclude.tag_ids),
                        )
                    )
                )
            )

            query = (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(
                    and_(
                        ~col(SampleTable.tags).any(
                            and_(
                                TagTable.kind == "sample",
                                db_array.in_array(
                                    column=col(TagTable.tag_id), values=exclude.tag_ids
                                ),
                            )
                        ),
                        ~col(SampleTable.sample_id).in_(annotation_tag_subquery),
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )
        elif exclude.sample_ids:
            query = (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(
                    ~db_array.in_array(column=col(ImageTable.sample_id), values=exclude.sample_ids)
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )
        elif exclude.annotation_ids:
            query = (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(
                    or_(
                        ~col(SampleTable.annotations).any(),
                        ~col(SampleTable.annotations).any(
                            db_array.in_array(
                                column=col(AnnotationBaseTable.sample_id),
                                values=exclude.annotation_ids,
                            )
                        ),
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

    if active_view_subquery is not None:
        query = query.where(col(SampleTable.sample_id).in_(active_view_subquery))

    return query
