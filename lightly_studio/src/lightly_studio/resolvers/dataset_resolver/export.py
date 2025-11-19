"""Resolver functions for exporting dataset samples based on filters."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session, and_, col, func, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable


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
    query = _build_export_query(dataset_id=dataset_id, include=include, exclude=exclude)
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
    query = _build_export_query(dataset_id=dataset_id, include=include, exclude=exclude)
    count_query = select(func.count()).select_from(query.subquery())
    return session.exec(count_query).one() or 0


def _build_export_query(  # noqa: C901
    dataset_id: UUID,
    include: ExportFilter | None = None,
    exclude: ExportFilter | None = None,
) -> SelectOfScalar[ImageTable]:
    """Build the export query based on filters.

    Args:
        session: SQLAlchemy session.
        dataset_id: UUID of the dataset.
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
            return (
                select(ImageTable)
                .join(ImageTable.sample)
                .join(SampleTable.annotations)
                .where(AnnotationBaseTable.dataset_id == dataset_id)
                .where(col(AnnotationBaseTable.annotation_id).in_(include.annotation_ids))
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
                            col(AnnotationBaseTable.annotation_id).in_(exclude.annotation_ids)
                        ),
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

    raise ValueError("Invalid include or export filter combination.")
