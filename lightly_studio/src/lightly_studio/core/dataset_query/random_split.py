"""Random, proportional splitting of samples into named tags.

A split assigns a set of input samples to named groups (e.g. ``train`` / ``val`` /
``test``) at random, in proportions given as relative parts. Splits are stored as
ordinary sample tags: each split name becomes a tag, and every input sample is
linked to exactly one of the split tags. Re-running a split first removes the
target split tags from the input samples, so the assignment is overwritten rather
than accumulated.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver

# Upper bound for a randomly chosen seed. Matches the range accepted by
# ``random.Random`` and keeps the value comfortably within a 32-bit integer.
_MAX_SEED = 2**32 - 1


@dataclass(frozen=True)
class SplitResult:
    """Summary of a completed split.

    Attributes:
        counts: Number of samples assigned to each split, keyed by split name and
            ordered the same as the input ``sizes``.
        seed: The seed that was used for the random assignment. Equal to the
            provided seed, or the randomly chosen one when no seed was given.
    """

    counts: dict[str, int]
    seed: int


def random_split(
    session: Session,
    collection_id: UUID,
    sample_ids: Sequence[UUID],
    sizes: Mapping[str, float],
    seed: int | None = None,
) -> SplitResult:
    """Randomly assign ``sample_ids`` to named split tags by proportion.

    Args:
        session: Database session used to read and write tags.
        collection_id: Collection the split tags belong to.
        sample_ids: The input samples to partition.
        sizes: Mapping of split name to relative parts. Values must all be
            positive; they need not sum to any particular total.
        seed: Seed for the deterministic shuffle. A random seed is chosen when
            ``None``; the effective seed is always reported in the result.

    Returns:
        A :class:`SplitResult` with the per-split counts and the effective seed.

    Raises:
        ValueError: If ``sizes`` is empty, contains a non-positive value, or has
            an empty split name.
    """
    validate_sizes(sizes)
    effective_seed = seed if seed is not None else random.randrange(_MAX_SEED)

    # Empty input set: report the split names with zero counts without touching
    # any tags.
    if not sample_ids:
        return SplitResult(counts=dict.fromkeys(sizes, 0), seed=effective_seed)

    assignment = _assign_sample_ids(sample_ids=sample_ids, sizes=sizes, seed=effective_seed)
    _write_splits(session=session, collection_id=collection_id, assignment=assignment)

    counts = {name: len(ids) for name, ids in assignment.items()}
    return SplitResult(counts=counts, seed=effective_seed)


def validate_sizes(sizes: Mapping[str, float]) -> None:
    """Validate split sizes.

    Args:
        sizes: Mapping of split name to relative parts.

    Raises:
        ValueError: If ``sizes`` is empty, has an empty split name, or contains a
            non-positive value.
    """
    if not sizes:
        raise ValueError("sizes must not be empty.")

    for name, value in sizes.items():
        if not name.strip():
            raise ValueError("Split names must be non-empty.")
        if value <= 0:
            raise ValueError(f"Split size for '{name}' must be greater than 0, got {value}.")


def partition_counts(total: int, sizes: Mapping[str, float]) -> dict[str, int]:
    """Split ``total`` into per-split counts using the largest-remainder method.

    Each split gets the floor of its exact proportional share, then the leftover
    units are handed out one at a time to the splits with the largest fractional
    remainder. This guarantees the counts sum exactly to ``total``.

    Args:
        total: The number of items to distribute.
        sizes: Mapping of split name to relative parts.

    Returns:
        Mapping of split name to count, ordered the same as ``sizes`` and summing
        to ``total``.
    """
    size_sum = sum(sizes.values())
    exact_shares = {name: total * value / size_sum for name, value in sizes.items()}
    counts = {name: int(share) for name, share in exact_shares.items()}

    leftover = total - sum(counts.values())
    by_remainder = sorted(sizes, key=lambda name: exact_shares[name] - counts[name], reverse=True)
    for name in by_remainder[:leftover]:
        counts[name] += 1
    return counts


def _assign_sample_ids(
    sample_ids: Sequence[UUID], sizes: Mapping[str, float], seed: int
) -> dict[str, list[UUID]]:
    """Shuffle the input ids deterministically and slice them per split."""
    shuffled = list(sample_ids)
    random.Random(seed).shuffle(shuffled)

    counts = partition_counts(total=len(shuffled), sizes=sizes)
    assignment: dict[str, list[UUID]] = {}
    start = 0
    for name, count in counts.items():
        assignment[name] = shuffled[start : start + count]
        start += count
    return assignment


def _write_splits(
    session: Session, collection_id: UUID, assignment: Mapping[str, list[UUID]]
) -> None:
    """Overwrite the split tags with the given assignment.

    For each split tag, the tag is first removed from the entire input set and
    then linked to only its assigned samples, so re-running replaces the previous
    assignment instead of accumulating.
    """
    input_sample_ids = [sample_id for ids in assignment.values() for sample_id in ids]
    for name, ids in assignment.items():
        tag = tag_resolver.get_or_create_sample_tag_by_name(
            session=session, collection_id=collection_id, tag_name=name
        )
        tag_resolver.remove_sample_ids_from_tag_id(
            session=session, tag_id=tag.tag_id, sample_ids=input_sample_ids
        )
        tag_resolver.add_sample_ids_to_tag_id(session=session, tag_id=tag.tag_id, sample_ids=ids)
