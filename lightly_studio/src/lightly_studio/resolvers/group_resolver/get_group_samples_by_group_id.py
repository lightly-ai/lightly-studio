"""Implementation of get_group_samples_by_group_id resolver function."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.group import (
    SampleGroupLinkTable,
)
from lightly_studio.models.sample import SampleTable


def get_group_samples_by_group_id(
    session: Session,
    group_id: UUID,
) -> Sequence[SampleTable]:
    """Get all component samples that belong to a group.

    This function retrieves all individual samples that are linked to a parent group sample
    through the SampleGroupLinkTable. Group samples are composite samples that contain
    multiple component samples (e.g., a group of related images or frames).

    Args:
        session: The database session used to execute the query.
        group_id: The UUID of the parent group sample whose components should be retrieved.

    Returns:
        A sequence of SampleTable objects representing all component samples that belong
        to the specified group sample. Returns an empty sequence if no components are found.

    """
    # Get component samples
    statement = (
        select(SampleTable)
        .join(SampleGroupLinkTable)
        .where(
            SampleGroupLinkTable.sample_id == SampleTable.sample_id,
            SampleGroupLinkTable.parent_sample_id == group_id,
        )
    )

    return session.exec(statement).all()
