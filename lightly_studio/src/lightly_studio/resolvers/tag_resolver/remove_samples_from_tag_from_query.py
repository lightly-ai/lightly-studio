"""Implementation of remove_samples_from_tag_from_query function for tags."""

from __future__ import annotations

from uuid import UUID

import sqlmodel
from sqlmodel import Session, col
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.utils import batching


def remove_samples_from_tag_from_query(
    session: Session,
    tag_id: UUID,
    sample_ids_query: SelectOfScalar[UUID],
) -> None:
    """Remove every sample matched by ``sample_ids_query`` from a tag.

    The matched ids are read first and deleted in batches, so the delete never
    depends on the query's own tables.
    """
    sample_ids = list(session.exec(sample_ids_query).all())
    for batch in batching.batched(items=sample_ids):
        session.exec(
            sqlmodel.delete(SampleTagLinkTable).where(
                col(SampleTagLinkTable.tag_id) == tag_id,
                col(SampleTagLinkTable.sample_id).in_(batch),
            )
        )
    session.commit()
