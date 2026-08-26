"""Resolves metadata balancing strategies into distributions for the sampling algorithm."""

from __future__ import annotations

import enum
import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session
from typing_extensions import TypeAlias

from lightly_studio.models.metadata import CATEGORICAL_TYPE_NAMES
from lightly_studio.resolvers.metadata_resolver import sample as sample_metadata_resolver
from lightly_studio.sampling.sampling_config import MetadataBalancingStrategy

logger = logging.getLogger(__name__)

# Upper bound on the number of balanced values. The distribution matrix holds one column
# per value, so an unbounded key such as a file path would allocate a column per sample.
# The most frequent values are balanced and the remaining ones are grouped as "other".
MAX_BALANCED_VALUES = 100


class _OtherValue(enum.Enum):
    """Column that groups all metadata values without their own target."""

    OTHER = enum.auto()


# Column key of the "other" group. Distinct from every metadata value, which are all strings.
_OTHER = _OtherValue.OTHER

_ColumnKey: TypeAlias = "str | _OtherValue"


def get_metadata_balancing_data(
    session: Session,
    strat: MetadataBalancingStrategy,
    collection_id: UUID,
    input_sample_ids: Sequence[UUID],
) -> tuple[NDArray[np.float32], list[float]]:
    """Build the value distributions and target distribution for metadata balancing.

    Every sample has at most one value for the key, so its row is one-hot. Samples
    without a value for the key get an all-zero row: they do not influence the
    balancing, but stay available for selection.

    N is the number of input samples and V is the number of balanced values.

    Args:
        session: The database session.
        strat: The metadata balancing strategy to resolve.
        collection_id: The collection the input samples belong to.
        input_sample_ids: The samples to sample from, in selection order.

    Returns:
        Tuple of:
            The value distributions of shape (N, V) and dtype `np.float32`.
            The target distribution of length V.

    Raises:
        ValueError: If the key does not exist in the collection or is not categorical.
    """
    sample_id_to_value = _get_categorical_values(
        session=session,
        metadata_key=strat.metadata_key,
        collection_id=collection_id,
        input_sample_ids=input_sample_ids,
    )
    value_counts = Counter(sample_id_to_value.values())
    if not value_counts:
        # No input sample has a value for the key, so there is nothing to balance.
        return np.zeros((len(input_sample_ids), 0), dtype=np.float32), []

    if strat.target_distribution == "uniform":
        target_keys = list(_get_balanced_counts(value_counts=value_counts))
        target_values = [1.0 / len(target_keys)] * len(target_keys)
    elif strat.target_distribution == "input":
        balanced_counts = _get_balanced_counts(value_counts=value_counts)
        target_keys = list(balanced_counts)
        target_values = [float(count) for count in balanced_counts.values()]
    else:
        target_keys, target_values = _get_explicit_target(
            target_distribution=strat.target_distribution,
            value_counts=value_counts,
        )

    value_distributions = _build_value_distributions(
        input_sample_ids=input_sample_ids,
        sample_id_to_value=sample_id_to_value,
        target_keys=target_keys,
    )
    return value_distributions, target_values


def _get_categorical_values(
    session: Session,
    metadata_key: str,
    collection_id: UUID,
    input_sample_ids: Sequence[UUID],
) -> dict[UUID, str]:
    """Resolve the categorical metadata value of every input sample that has one.

    Values are returned as strings so that booleans and strings share one column type.

    Raises:
        ValueError: If the key does not exist in the collection or is not categorical.
    """
    # TODO(Nauryzbay, 08/2026): This resolves the values of the whole collection. Scope the
    # query to `input_sample_ids` if it becomes a bottleneck for heavily filtered samplings.
    all_values, metadata_type = sample_metadata_resolver.get_metadata_values_for_key(
        session=session,
        collection_id=collection_id,
        key=metadata_key,
    )
    if metadata_type is None:
        raise ValueError(
            f"Metadata key '{metadata_key}' does not exist in collection {collection_id}."
        )
    if metadata_type not in CATEGORICAL_TYPE_NAMES:
        raise ValueError(
            f"Metadata key '{metadata_key}' has type '{metadata_type}', but balancing "
            f"requires one of {CATEGORICAL_TYPE_NAMES}."
        )

    return {
        sample_id: _format_value(all_values[sample_id])
        for sample_id in input_sample_ids
        if sample_id in all_values
    }


def _format_value(value: str | bool) -> str:
    """Format a categorical metadata value as its column key."""
    if isinstance(value, bool):
        # Match the lowercase spelling used when metadata values are read as text.
        return "true" if value else "false"
    return value


def _get_balanced_counts(value_counts: Mapping[str, int]) -> dict[_ColumnKey, int]:
    """Count the samples per balanced value, grouping the rarest values if there are many.

    Returns:
        The sample count per balanced value, in sorted value order. An "other" entry
        holding the combined count of the rarest values is appended when the key has
        more than `MAX_BALANCED_VALUES` distinct values.
    """
    if len(value_counts) <= MAX_BALANCED_VALUES:
        return {value: value_counts[value] for value in sorted(value_counts)}

    most_common = Counter(value_counts).most_common(MAX_BALANCED_VALUES)
    balanced_counts: dict[_ColumnKey, int] = dict(sorted(most_common))
    balanced_counts[_OTHER] = sum(value_counts.values()) - sum(count for _, count in most_common)
    logger.warning(
        f"Metadata balancing found {len(value_counts)} distinct values, but balances at most "
        f"{MAX_BALANCED_VALUES}. The {len(value_counts) - MAX_BALANCED_VALUES} rarest values "
        f"are balanced together as one group."
    )
    return balanced_counts


def _get_explicit_target(
    target_distribution: Mapping[str, float],
    value_counts: Mapping[str, int],
) -> tuple[list[_ColumnKey], list[float]]:
    """Resolve an explicit target distribution.

    Values with a target keep it. All other values of the key are grouped as "other"
    and share the target remaining to 1.0.
    """
    target_keys: list[_ColumnKey] = list(target_distribution)
    target_values = list(target_distribution.values())

    if set(value_counts) - set(target_distribution):
        target_keys.append(_OTHER)
        target_values.append(max(1.0 - sum(target_distribution.values()), 0.0))
    return target_keys, target_values


def _build_value_distributions(
    input_sample_ids: Sequence[UUID],
    sample_id_to_value: Mapping[UUID, str],
    target_keys: Sequence[_ColumnKey],
) -> NDArray[np.float32]:
    """Build the one-hot value distributions of the input samples.

    N is the number of input samples and V is the number of balanced values.

    Returns:
        The value distributions of shape (N, V) and dtype `np.float32`. Samples without a
        value for the key have an all-zero row.
    """
    value_to_column = {value: column for column, value in enumerate(target_keys)}
    other_column = value_to_column.get(_OTHER)

    value_distributions = np.zeros((len(input_sample_ids), len(target_keys)), dtype=np.float32)
    for row, sample_id in enumerate(input_sample_ids):
        value = sample_id_to_value.get(sample_id)
        if value is None:
            continue
        column = value_to_column.get(value, other_column)
        if column is not None:
            value_distributions[row, column] = 1.0
    return value_distributions
