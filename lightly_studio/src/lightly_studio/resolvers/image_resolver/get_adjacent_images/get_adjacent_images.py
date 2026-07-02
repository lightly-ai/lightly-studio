"""Public entry point for adjacency lookup and the fast-path/fallback dispatch."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.resolvers import similarity_utils
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
        The adjacency result, or ``None`` if the anchor is not in the (filtered)
        collection.
    """
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


def _is_keyset_sortable(order_by: list[OrderByExpression] | None) -> bool:
    """Return whether the sort can be served by the keyset seek path.

    Keyset comparison needs non-nullable, single-column sort keys. Plain image
    columns (``OrderByField``) qualify; metadata / evaluation-metric sorts use
    outer joins and nullable values, so they keep the window implementation.
    """
    if not order_by:
        return True
    return all(isinstance(expr, OrderByField) for expr in order_by)
