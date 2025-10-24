"""Handler for database operations related to datasets."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session, and_, col, func, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.dataset import DatasetCreate, DatasetTable, DatasetViewWithCount
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


def create(session: Session, dataset: DatasetCreate) -> DatasetTable:
    """Create a new dataset in the database."""
    existing = get_by_name(session=session, name=dataset.name)
    if existing:
        raise ValueError(f"Dataset with name '{dataset.name}' already exists.")
    db_dataset = DatasetTable.model_validate(dataset)
    session.add(db_dataset)
    session.commit()
    session.refresh(db_dataset)
    return db_dataset


# TODO(Michal, 06/2025): Use Paginated struct instead of offset and limit
def get_all(session: Session, offset: int = 0, limit: int = 100) -> list[DatasetTable]:
    """Retrieve all datasets with pagination."""
    datasets = session.exec(
        select(DatasetTable)
        .order_by(col(DatasetTable.created_at).asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(datasets) if datasets else []


def get_by_id(session: Session, dataset_id: UUID) -> DatasetTable | None:
    """Retrieve a single dataset by ID."""
    return session.exec(
        select(DatasetTable).where(DatasetTable.dataset_id == dataset_id)
    ).one_or_none()


def get_by_name(session: Session, name: str) -> DatasetTable | None:
    """Retrieve a single dataset by name."""
    return session.exec(select(DatasetTable).where(DatasetTable.name == name)).one_or_none()


def update(session: Session, dataset_id: UUID, dataset_data: DatasetCreate) -> DatasetTable:
    """Update an existing dataset."""
    dataset = get_by_id(session=session, dataset_id=dataset_id)
    if not dataset:
        raise ValueError(f"Dataset ID was not found '{dataset_id}'.")

    dataset.name = dataset_data.name
    dataset.updated_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(dataset)
    return dataset


def delete(session: Session, dataset_id: UUID) -> bool:
    """Delete a dataset."""
    dataset = get_by_id(session=session, dataset_id=dataset_id)
    if not dataset:
        return False

    session.delete(dataset)
    session.commit()
    return True


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
                .where(ImageTable.dataset_id == dataset_id)
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
                        col(ImageTable.annotations).any(
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
                .where(ImageTable.dataset_id == dataset_id)
                .where(col(ImageTable.sample_id).in_(include.sample_ids))
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

        # get samples by specific annotation_ids
        if include.annotation_ids:
            return (
                select(ImageTable)
                .join(ImageTable.annotations)
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
                .where(ImageTable.dataset_id == dataset_id)
                .where(
                    and_(
                        ~col(SampleTable.tags).any(
                            and_(
                                TagTable.kind == "sample",
                                col(TagTable.tag_id).in_(exclude.tag_ids),
                            )
                        ),
                        or_(
                            ~col(ImageTable.annotations).any(),
                            ~col(ImageTable.annotations).any(
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
                .where(ImageTable.dataset_id == dataset_id)
                .where(col(ImageTable.sample_id).notin_(exclude.sample_ids))
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )
        if exclude.annotation_ids:
            return (
                select(ImageTable)
                .where(ImageTable.dataset_id == dataset_id)
                .where(
                    or_(
                        ~col(ImageTable.annotations).any(),
                        ~col(ImageTable.annotations).any(
                            col(AnnotationBaseTable.annotation_id).in_(exclude.annotation_ids)
                        ),
                    )
                )
                .order_by(col(ImageTable.created_at).asc())
                .distinct()
            )

    raise ValueError("Invalid include or export filter combination.")


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
