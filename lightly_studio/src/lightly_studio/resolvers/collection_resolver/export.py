"""Resolver functions for exporting collection samples based on filters."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session, and_, col, func, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.collection_resolver.get_hierarchy import get_hierarchy


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
) -> list[str]:
    """Retrieve samples for exporting from a collection.

    Only one of include or exclude should be set and not both.
    Furthermore, the include and exclude filter can only have
    one type (tag_ids, sample_ids or annotations_ids) set.

    Args:
        session: SQLAlchemy session.
        collection_id: UUID of the collection.
        include: Filter to include samples.
        exclude: Filter to exclude samples.

    Returns:
        List of file paths
    """
    # Get all child collection IDs that could contain annotations
    annotation_collection_ids = _get_annotation_collection_ids(session, collection_id)
    query = _build_export_query(
        collection_id=collection_id,
        annotation_collection_ids=annotation_collection_ids,
        include=include,
        exclude=exclude,
    )
    result = session.exec(query).all()
    return [sample.file_path_abs for sample in result]


def get_filtered_samples_count(
    session: Session,
    collection_id: UUID,
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
) -> int:
    """Get statistics about the export query.

    Only one of include or exclude should be set and not both.
    Furthermore, the include and exclude filter can only have
    one type (tag_ids, sample_ids or annotations_ids) set.

    Args:
        session: SQLAlchemy session.
        collection_id: UUID of the collection.
        include: Filter to include samples.
        exclude: Filter to exclude samples.

    Returns:
        Count of files to be exported
    """
    # Get all child collection IDs that could contain annotations
    annotation_collection_ids = _get_annotation_collection_ids(session, collection_id)
    query = _build_export_query(
        collection_id=collection_id,
        annotation_collection_ids=annotation_collection_ids,
        include=include,
        exclude=exclude,
    )
    count_query = select(func.count()).select_from(query.subquery())
    return session.exec(count_query).one() or 0


def _get_annotation_collection_ids(session: Session, collection_id: UUID) -> list[UUID]:
    """Get all child collection IDs that could contain annotations.

    This includes the collection itself and all its child collections (recursively)
    that have sample_type ANNOTATION.

    Args:
        session: SQLAlchemy session.
        collection_id: UUID of the root collection.

    Returns:
        List of collection IDs that could contain annotations.
    """
    hierarchy = get_hierarchy(session, collection_id)
    return [col.collection_id for col in hierarchy if col.sample_type == SampleType.ANNOTATION]


def _build_export_query(  # noqa: C901
    collection_id: UUID,
    annotation_collection_ids: list[UUID],
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
) -> SelectOfScalar[ImageTable]:
    """Build the export query based on filters.

    Args:
        collection_id: UUID of the collection.
        annotation_collection_ids: List of collection IDs that could contain annotations.
        include: Filter to include samples.
        exclude: Filter to exclude samples.

    Returns:
        SQLModel select query
    """
    if not include and not exclude:
        raise ValueError("Include or exclude filter is required.")
    if include and exclude:
        raise ValueError("Cannot include and exclude at the same time.")

    # include tags or sample_ids or annotation_ids from result
    if include:
        if include.tag_ids:
            return (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(
                    or_(
                        # Samples with matching sample tags
                        col(SampleTable.tags).any(
                            and_(
                                TagTable.kind == "sample",
                                col(TagTable.tag_id).in_(include.tag_ids),
                            )
                        ),
                        # Samples with matching annotation tags
                        col(SampleTable.annotations).any(
                            col(AnnotationBaseTable.tags).any(
                                and_(
                                    TagTable.kind == "annotation",
                                    col(TagTable.tag_id).in_(include.tag_ids),
                                )
                            )
                        ),
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

        # get samples by specific sample_ids
        if include.sample_ids:
            return (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(col(ImageTable.sample_id).in_(include.sample_ids))
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

        # get samples by specific annotation_ids
        if include.annotation_ids:
            # Annotations are stored in child collections, so filter by all annotation collection
            # IDs
            # Filter by checking if the annotation's sample_id belongs to a sample in
            # annotation_collection_ids
            annotation_sample_subquery = select(SampleTable.sample_id).where(
                col(SampleTable.collection_id).in_(annotation_collection_ids)
            )
            return (
                select(ImageTable)
                .join(ImageTable.sample)
                .join(SampleTable.annotations)
                .where(col(AnnotationBaseTable.sample_id).in_(annotation_sample_subquery))
                .where(col(AnnotationBaseTable.sample_id).in_(include.annotation_ids))
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

    # exclude tags or sample_ids or annotation_ids from result
    elif exclude:
        if exclude.tag_ids:
            return (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(
                    and_(
                        ~col(SampleTable.tags).any(
                            and_(
                                TagTable.kind == "sample",
                                col(TagTable.tag_id).in_(exclude.tag_ids),
                            )
                        ),
                        or_(
                            ~col(SampleTable.annotations).any(),
                            ~col(SampleTable.annotations).any(
                                col(AnnotationBaseTable.tags).any(
                                    and_(
                                        TagTable.kind == "annotation",
                                        col(TagTable.tag_id).in_(exclude.tag_ids),
                                    )
                                )
                            ),
                        ),
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )
        if exclude.sample_ids:
            return (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(col(ImageTable.sample_id).notin_(exclude.sample_ids))
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )
        if exclude.annotation_ids:
            return (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == collection_id)
                .where(
                    or_(
                        ~col(SampleTable.annotations).any(),
                        ~col(SampleTable.annotations).any(
                            col(AnnotationBaseTable.sample_id).in_(exclude.annotation_ids)
                        ),
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

    raise ValueError("Invalid include or export filter combination.")
