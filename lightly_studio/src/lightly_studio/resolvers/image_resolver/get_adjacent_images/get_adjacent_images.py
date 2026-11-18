"""Public entry point for adjacency lookup and the fast-path/fallback dispatch."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.resolvers import similarity_utils, workflow_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.get_adjacent_images.get_adjacent_images_keyset import (
    get_adjacent_images_keyset,
)
from lightly_studio.resolvers.image_resolver.get_adjacent_images.get_adjacent_images_window import (
    get_adjacent_images_window,
)


def get_adjacent_images(  # noqa: PLR0913
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None = None,
    text_embedding: list[float] | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> AdjacentResultView | None:
    """Get the previous and next image for a sample in the current sort order.

    Uses a keyset (seek) lookup for the common case — the default ``file_path_abs``
    sort or any sort over plain image columns — so prev/next and the position/total
    counts avoid the full sort + window scan over the whole collection.
    Similarity search and joined/nullable sorts (metadata, evaluation metrics) fall
    back to the window-function implementation.

    Args:
        session: Database session.
        sample_id: The anchor sample whose neighbours we want.
        collection_id: Collection the anchor and neighbours belong to.
        filters: Optional image filters constraining the collection.
        text_embedding: Text embedding for similarity search; forces the window path.
        order_by: Requested sort; ``None`` means the default ``file_path_abs`` sort.

    Returns:
        The adjacency result, or ``None`` if the anchor is not in the collection. An
        anchor that no longer matches the filters (e.g. a reviewer accepted it under an
        "In review" filter) keeps its place: its neighbours are the closest matching
        samples in the sort order, and it still counts in the position and total.
    """
    # Look the project up once: for the workflow status filter and the neighbours' batches.
    project_id = workflow_resolver.get_dataset_project_id(
        session=session, collection_id=collection_id
    )
    workflow_resolver.set_filter_project_id(filters=filters, project_id=project_id)
    result = _get_adjacent_images(
        session=session,
        sample_id=sample_id,
        collection_id=collection_id,
        filters=filters,
        text_embedding=text_embedding,
        order_by=order_by,
    )
    if result is None or project_id is None:
        return result
    return _with_neighbour_workflow(session=session, result=result, project_id=project_id)


def _get_adjacent_images(  # noqa: PLR0913
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None,
    text_embedding: list[float] | None,
    order_by: list[OrderByExpression] | None,
) -> AdjacentResultView | None:
    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    is_similarity_search = distance_expr is not None or embedding_model_id is not None
    if not is_similarity_search and _is_keyset_sortable(order_by):
        return get_adjacent_images_keyset(
            session=session,
            sample_id=sample_id,
            collection_id=collection_id,
            filters=filters,
            order_by=order_by,
        )

    return get_adjacent_images_window(
        session=session,
        sample_id=sample_id,
        collection_id=collection_id,
        filters=filters,
        distance_expr=distance_expr,
        embedding_model_id=embedding_model_id,
        order_by=order_by,
    )


def _with_neighbour_workflow(
    session: Session, result: AdjacentResultView, project_id: UUID
) -> AdjacentResultView:
    """Add the neighbours' batch and state, so the detail view can open them in workflow mode."""
    neighbour_ids = [
        neighbour_id
        for neighbour_id in (result.previous_sample_id, result.next_sample_id)
        if neighbour_id is not None
    ]
    workflows = workflow_resolver.get_samples_workflow(
        session=session, project_id=project_id, sample_ids=neighbour_ids
    )
    return result.model_copy(
        update={
            "previous_workflow": workflows.get(result.previous_sample_id)
            if result.previous_sample_id
            else None,
            "next_workflow": workflows.get(result.next_sample_id)
            if result.next_sample_id
            else None,
        }
    )


def _is_keyset_sortable(order_by: list[OrderByExpression] | None) -> bool:
    """Return whether the sort can be served by the keyset seek path.

    Keyset comparison needs non-nullable, single-column sort keys. Plain image
    columns (``OrderByField``) qualify; metadata / evaluation-metric sorts use
    outer joins and nullable values, so they keep the window implementation.
    """
    if not order_by:
        return True
    return all(isinstance(expr, OrderByField) for expr in order_by)
