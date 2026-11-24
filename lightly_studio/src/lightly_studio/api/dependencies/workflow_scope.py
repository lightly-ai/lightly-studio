"""Limit what a labeler account sees in the grid to the batch files it works on."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from lightly_studio.api.dependencies.identity import Identity, Role
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import workflow_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.services.sample_services.sample_adjacents_service import AdjacentRequest

GridFilter = TypeVar("GridFilter", ImageFilter, McapSequenceFilter)


def workflow_assignee(identity: Identity) -> str | None:
    """Returns whose batch files the workflow views show the user, or None for all files.

    A labeler account sees only the files it labels or reviews; other roles see every file.

    Args:
        identity: The user that sends the request.
    """
    return identity.email if identity.role == Role.LABELER else None


def scope_to_caller(
    identity: Identity, filters: GridFilter | None, empty: Callable[[], GridFilter]
) -> GridFilter | None:
    """Returns the grid filter of a request, limited to a labeler's own batch files.

    Other roles get the filter unchanged. A labeler without a filter gets `empty()`, limited.

    Args:
        identity: The user that sends the request.
        filters: The request's image or MCAP sequence filter, if any.
        empty: Builds a filter without conditions.
    """
    email = workflow_assignee(identity=identity)
    if email is None:
        return filters
    scoped = filters if filters is not None else empty()
    workflow_resolver.scope_to_assignee(filters=scoped, email=email)
    return scoped


def scope_adjacent_request(identity: Identity, request: AdjacentRequest) -> None:
    """Limits the neighbours of an image or MCAP sequence to a labeler's own batch files.

    Other sample types, and a request whose filter does not match its sample type, are left
    unchanged.

    Args:
        identity: The user that sends the request.
        request: The adjacents request to update in place.
    """
    filters = request.filters
    if request.sample_type == SampleType.IMAGE and isinstance(filters, ImageFilter | None):
        request.filters = scope_to_caller(identity=identity, filters=filters, empty=ImageFilter)
    elif request.sample_type == SampleType.SEQUENCE and isinstance(
        filters, McapSequenceFilter | None
    ):
        request.filters = scope_to_caller(
            identity=identity, filters=filters, empty=McapSequenceFilter
        )
