"""Helpers for MCAP group component definition resolver tests."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection


def create_mcap_group_components(
    session: Session,
) -> tuple[CollectionTable, dict[str, CollectionTable]]:
    """Create a GROUP with MCAP slots ``image`` and ``point_cloud``."""
    group = create_collection(session=session, sample_type=SampleType.GROUP)
    children = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=group.collection_id,
        components=[
            ("image", SampleType.MCAP),
            ("point_cloud", SampleType.MCAP),
        ],
    )
    return group, children


def create_classic_group_components(
    session: Session,
) -> tuple[CollectionTable, dict[str, CollectionTable]]:
    """Create a GROUP with classic IMAGE/VIDEO slots and no MCAP rows."""
    group = create_collection(session=session, sample_type=SampleType.GROUP)
    children = collection_resolver.create_group_components(
        session=session,
        parent_collection_id=group.collection_id,
        components=[("image", SampleType.IMAGE), ("video", SampleType.VIDEO)],
    )
    return group, children
