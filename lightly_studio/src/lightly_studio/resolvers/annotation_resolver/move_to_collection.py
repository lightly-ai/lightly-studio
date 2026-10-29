"""Move annotation samples to another annotation collection, keeping their IDs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Table, delete, insert, update
from sqlalchemy import select as sa_select
from sqlmodel import Session, SQLModel, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import tag_resolver
from lightly_studio.utils import batching

# Rows that reference an annotation sample, with the column that holds its ID. The rows that
# reference annotation_base come before it.
_ROWS_REFERENCING_SAMPLE: tuple[tuple[type[SQLModel], str], ...] = (
    (ObjectDetectionAnnotationTable, "sample_id"),
    (SegmentationAnnotationTable, "sample_id"),
    (Cuboid3DAnnotationTable, "sample_id"),
    (TemporalSpanTable, "sample_id"),
    (SampleEmbeddingTable, "sample_id"),
    (SampleTagLinkTable, "sample_id"),
    (SampleMetadataTable, "sample_id"),
    (CaptionTable, "parent_sample_id"),
    (AnnotationBaseTable, "sample_id"),
)


def move_to_collection(
    session: Session, annotation_ids: Sequence[UUID], collection_id: UUID
) -> None:
    """Set the collection of annotation samples and keep their IDs and dependent rows.

    DuckDB runs an update of an indexed column as a delete and an insert, and rejects it while
    other rows reference the sample. So the rows that reference the samples are read, deleted,
    and inserted again after the update. The move commits several times and is not atomic.
    Callers must delete the evaluation metrics of the annotations first.

    Tags belong to a collection, so a tag link moves to the tag with the same name in the
    target collection. The tag is created if it does not exist.

    Args:
        session: Database session.
        annotation_ids: IDs of existing annotations.
        collection_id: ID of the annotation collection to move the annotations to.
    """
    for batch in batching.batched(items=annotation_ids):
        rows_by_model = {
            model: _read_rows(session=session, model=model, column=column, ids=batch)
            for model, column in _ROWS_REFERENCING_SAMPLE
        }
        rows_by_model[SampleTagLinkTable] = _retarget_tag_links(
            session=session, rows=rows_by_model[SampleTagLinkTable], collection_id=collection_id
        )
        # DuckDB rejects the delete of a referenced row in the transaction that deleted the
        # referencing rows, so each foreign key level is committed separately.
        for model, column in _ROWS_REFERENCING_SAMPLE:
            table = _table(model)
            session.execute(delete(table).where(table.c[column].in_(batch)))
            session.commit()
        sample_table = _table(SampleTable)
        session.execute(
            update(sample_table)
            .where(sample_table.c["sample_id"].in_(batch))
            .values(collection_id=collection_id)
        )
        session.commit()
        # Insert in reverse order, so that annotation_base rows come before their details.
        for model, _ in reversed(_ROWS_REFERENCING_SAMPLE):
            if rows_by_model[model]:
                session.execute(insert(_table(model)), rows_by_model[model])
        session.commit()
    session.expire_all()


def _table(model: type[SQLModel]) -> Table:
    return model.__table__  # type: ignore[attr-defined, no-any-return]


def _read_rows(
    session: Session, model: type[SQLModel], column: str, ids: Sequence[UUID]
) -> list[dict[str, Any]]:
    table = _table(model)
    rows = session.execute(sa_select(table).where(table.c[column].in_(ids))).mappings().all()
    return [dict(row) for row in rows]


def _retarget_tag_links(
    session: Session, rows: list[dict[str, Any]], collection_id: UUID
) -> list[dict[str, Any]]:
    """Point tag links at the tags with the same names in the given collection."""
    tags = session.exec(
        select(TagTable).where(col(TagTable.tag_id).in_({row["tag_id"] for row in rows}))
    ).all()
    target_tag_ids = {
        tag.tag_id: tag_resolver.get_or_create_sample_tag_by_name(
            session=session, collection_id=collection_id, tag_name=tag.name
        ).tag_id
        for tag in tags
    }
    return [{**row, "tag_id": target_tag_ids[row["tag_id"]]} for row in rows]
