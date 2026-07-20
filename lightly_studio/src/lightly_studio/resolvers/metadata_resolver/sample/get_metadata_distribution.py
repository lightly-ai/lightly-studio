"""Resolver computing the distribution of a single metadata key.

Categorical (``string``/``boolean``) keys produce value/count pairs including an
explicit ``(none)`` entry for samples missing the key. Numeric
(``integer``/``float``) keys produce an equal-width histogram whose edges span
the key's global (unfiltered) min/max so that per-filter series share an x-axis.
"""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.errors import (
    MetadataKeyNotFoundError,
    UnsupportedMetadataTypeError,
)
from lightly_studio.models.metadata import (
    MetadataCategoricalCount,
    MetadataDistributionView,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_info import (
    CATEGORICAL_METADATA_TYPES,
    format_categorical_value,
)
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_values_for_key import (
    get_metadata_values_for_key,
)

DEFAULT_BINS = 25
NONE_LABEL = "(none)"
NUMERIC_METADATA_TYPES = ("integer", "float")

# A histogram needs at least a lower and an upper edge to define one bin.
_MIN_BIN_EDGES = 2


def get_metadata_distribution(
    session: Session,
    collection_id: UUID,
    key: str,
    *,
    scope_sample_ids: set[UUID] | None = None,
    bins: int = DEFAULT_BINS,
) -> MetadataDistributionView:
    """Compute the distribution of a metadata key over a set of samples.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        key: The metadata key to aggregate.
        scope_sample_ids: The samples to aggregate over. ``None`` aggregates over
            every sample in the collection.
        bins: Number of equal-width bins for numeric keys.

    Returns:
        A ``MetadataDistributionView`` with either the categorical or numeric
        payload populated.

    Raises:
        MetadataKeyNotFoundError: If the key is absent from the collection.
        UnsupportedMetadataTypeError: If the key's type is neither categorical
            nor numeric.
    """
    sample_to_value, metadata_type = get_metadata_values_for_key(
        session=session, collection_id=collection_id, key=key
    )
    if metadata_type is None:
        raise MetadataKeyNotFoundError(
            f"Metadata key '{key}' not found in collection {collection_id}."
        )

    scope = (
        scope_sample_ids
        if scope_sample_ids is not None
        else _all_collection_sample_ids(session=session, collection_id=collection_id)
    )

    if metadata_type in CATEGORICAL_METADATA_TYPES:
        return _categorical_distribution(
            key=key, metadata_type=metadata_type, sample_to_value=sample_to_value, scope=scope
        )
    if metadata_type in NUMERIC_METADATA_TYPES:
        return _numeric_distribution(
            key=key,
            metadata_type=metadata_type,
            sample_to_value=sample_to_value,
            scope=scope,
            bins=bins,
        )

    raise UnsupportedMetadataTypeError(
        f"Metadata key '{key}' has type {metadata_type!r}, which has no distribution. "
        f"Supported types: {(*CATEGORICAL_METADATA_TYPES, *NUMERIC_METADATA_TYPES)}."
    )


def _all_collection_sample_ids(session: Session, collection_id: UUID) -> set[UUID]:
    """Return the ids of every sample in the collection."""
    return set(
        session.exec(
            select(SampleTable.sample_id).where(col(SampleTable.collection_id) == collection_id)
        ).all()
    )


def _categorical_distribution(
    key: str,
    metadata_type: str,
    sample_to_value: dict[UUID, object],
    scope: set[UUID],
) -> MetadataDistributionView:
    """Count categorical values within scope, including a ``(none)`` entry."""
    counts: Counter[str] = Counter()
    for sample_id in scope:
        if sample_id in sample_to_value:
            counts[format_categorical_value(sample_to_value[sample_id])] += 1

    none_count = len(scope) - sum(counts.values())

    # Highest count first, ties broken alphabetically for stable display.
    categorical = [
        MetadataCategoricalCount(value=value, count=count)
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    categorical.append(MetadataCategoricalCount(value=NONE_LABEL, count=none_count))

    return MetadataDistributionView(
        key=key, type=metadata_type, kind="categorical", categorical=categorical
    )


def _numeric_distribution(
    key: str,
    metadata_type: str,
    sample_to_value: dict[UUID, object],
    scope: set[UUID],
    bins: int,
) -> MetadataDistributionView:
    """Bin in-scope numeric values into equal-width bins over the global range.

    Bin edges span the key's global (unfiltered) min/max so that separately
    filtered series (e.g. one per tag) share the same x-axis.
    """
    global_values = [float(value) for value in sample_to_value.values()]  # type: ignore[arg-type]
    in_scope_values = [
        float(sample_to_value[sample_id])  # type: ignore[arg-type]
        for sample_id in scope
        if sample_id in sample_to_value
    ]
    none_count = len(scope) - len(in_scope_values)

    bin_edges = build_bin_edges(global_values=global_values, bins=bins)
    counts = bin_counts(values=in_scope_values, bin_edges=bin_edges)

    return MetadataDistributionView(
        key=key,
        type=metadata_type,
        kind="numeric",
        bin_edges=bin_edges,
        counts=counts,
        none_count=none_count,
    )


def build_bin_edges(global_values: list[float], bins: int) -> list[float]:
    """Build ``bins + 1`` equal-width edges spanning the global value range."""
    bins = max(bins, 1)
    if not global_values:
        return []

    minimum = min(global_values)
    maximum = max(global_values)
    # Degenerate range (single distinct value): widen it so we still get a bin.
    if maximum <= minimum:
        maximum = minimum + 1.0

    width = (maximum - minimum) / bins
    return [minimum + width * index for index in range(bins + 1)]


def bin_counts(values: list[float], bin_edges: list[float]) -> list[int]:
    """Count ``values`` into the bins described by ``bin_edges``."""
    if len(bin_edges) < _MIN_BIN_EDGES:
        return []

    bins = len(bin_edges) - 1
    minimum = bin_edges[0]
    maximum = bin_edges[-1]
    width = (maximum - minimum) / bins
    counts = [0] * bins
    for value in values:
        index = int((value - minimum) / width) if width > 0 else 0
        # Clamp so the maximum value (and any float rounding) lands in the last bin.
        index = min(max(index, 0), bins - 1)
        counts[index] += 1
    return counts
