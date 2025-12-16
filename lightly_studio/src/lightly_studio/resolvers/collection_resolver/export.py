"""Resolver functions for exporting dataset samples based on filters."""

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
    dataset_id: UUID,
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
) -> list[str]:
    """Retrieve samples for exporting from a dataset.

    Only one of include or exclude should be set and not both.
    Furthermore, the include and exclude filter can only have
    one type (tag_ids, sample_ids or annotations_ids) set.

    Args:
        session: SQLAlchemy session.
        dataset_id: UUID of the dataset.
        include: Filter to include samples.
        exclude: Filter to exclude samples.

    Returns:
        List of file paths
    """
    # Get all child dataset IDs that could contain annotations
    annotation_dataset_ids = _get_annotation_dataset_ids(session, dataset_id)
    query = _build_export_query(
        dataset_id=dataset_id,
        annotation_dataset_ids=annotation_dataset_ids,
        include=include,
        exclude=exclude,
    )
    result = session.exec(query).all()
    return [sample.file_path_abs for sample in result]


def get_filtered_samples_count(
    session: Session,
    dataset_id: UUID,
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
) -> int:
    """Get statistics about the export query.

    Only one of include or exclude should be set and not both.
    Furthermore, the include and exclude filter can only have
    one type (tag_ids, sample_ids or annotations_ids) set.

    Args:
        session: SQLAlchemy session.
        dataset_id: UUID of the dataset.
        include: Filter to include samples.
        exclude: Filter to exclude samples.

    Returns:
        Count of files to be exported
    """
    # Get all child dataset IDs that could contain annotations
    annotation_dataset_ids = _get_annotation_dataset_ids(session, dataset_id)
    query = _build_export_query(
        dataset_id=dataset_id,
        annotation_dataset_ids=annotation_dataset_ids,
        include=include,
        exclude=exclude,
    )
    count_query = select(func.count()).select_from(query.subquery())
    return session.exec(count_query).one() or 0


def _get_annotation_dataset_ids(session: Session, dataset_id: UUID) -> list[UUID]:
    """Get all child dataset IDs that could contain annotations.

    This includes the dataset itself and all its child datasets (recursively)
    that have sample_type ANNOTATION.

    Args:
        session: SQLAlchemy session.
        dataset_id: UUID of the root dataset.

    Returns:
        List of dataset IDs that could contain annotations.
    """
    hierarchy = get_hierarchy(session, dataset_id)
    return [ds.collection_id for ds in hierarchy if ds.sample_type == SampleType.ANNOTATION]


def _build_export_query(  # noqa: C901
    dataset_id: UUID,
    annotation_dataset_ids: list[UUID],
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
) -> SelectOfScalar[ImageTable]:
    """Build the export query based on filters.

    Args:
        dataset_id: UUID of the dataset.
        annotation_dataset_ids: List of dataset IDs that could contain annotations.
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
                .where(SampleTable.dataset_id == dataset_id)
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
                .where(SampleTable.dataset_id == dataset_id)
                .where(col(ImageTable.sample_id).in_(include.sample_ids))
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

        # get samples by specific annotation_ids
        if include.annotation_ids:
            # Annotations are stored in child datasets, so filter by all annotation dataset IDs
            # Filter by checking if the annotation's sample_id belongs to a sample in
            # annotation_dataset_ids
            annotation_sample_subquery = select(SampleTable.sample_id).where(
                col(SampleTable.dataset_id).in_(annotation_dataset_ids)
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
                .where(SampleTable.dataset_id == dataset_id)
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
                .where(SampleTable.dataset_id == dataset_id)
                .where(col(ImageTable.sample_id).notin_(exclude.sample_ids))
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )
        if exclude.annotation_ids:
            return (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.dataset_id == dataset_id)
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
