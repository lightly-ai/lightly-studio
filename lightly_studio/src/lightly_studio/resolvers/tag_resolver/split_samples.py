"""Create a complete random partition of samples into new tags."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.tag import TagTable

_MINIMUM_SPLIT_COUNT = 2


@dataclass(frozen=True)
class SplitDefinition:
    """The name and relative size of one output tag."""

    tag_name: str
    relative_size: int


def split_samples(
    session: Session,
    collection_id: UUID,
    sample_ids: Sequence[UUID],
    splits: Sequence[SplitDefinition],
    seed: int | None = None,
) -> dict[str, int]:
    """Assign every supplied sample to exactly one newly-created tag.

    Args:
        session: Database session used for the complete mutation.
        collection_id: Collection owning both samples and output tags.
        sample_ids: Sample IDs to partition.
        splits: Ordered names and positive relative sizes for output tags.
        seed: Optional seed for reproducible assignments.

    Returns:
        The number of samples assigned to each tag, in split order.

    Raises:
        ValueError: If the split definitions or sample scope are invalid, or an output
            tag already exists.
    """
    normalized_splits = _validate_splits(splits=splits)
    unique_sample_ids = list(dict.fromkeys(sample_ids))
    if not unique_sample_ids:
        raise ValueError("Cannot split an empty sample scope.")

    existing_tag_id = session.exec(
        select(TagTable.tag_id)
        .where(TagTable.collection_id == collection_id)
        .where(col(TagTable.name).in_([split.tag_name for split in normalized_splits]))
    ).first()
    if existing_tag_id is not None:
        raise ValueError("One or more output tags already exist.")
    if len(unique_sample_ids) < len(normalized_splits):
        raise ValueError("The number of splits cannot exceed the number of matching samples.")

    # Sorting first makes a seeded split independent of the caller's sample ordering.
    unique_sample_ids.sort(key=str)
    random.Random(seed).shuffle(unique_sample_ids)
    counts = _allocate_counts(sample_count=len(unique_sample_ids), splits=normalized_splits)
    try:
        tags = [
            TagTable(name=split.tag_name, collection_id=collection_id, kind="sample")
            for split in normalized_splits
        ]
        session.add_all(tags)
        session.flush()
        start = 0
        for tag, count in zip(tags, counts):
            partition = unique_sample_ids[start : start + count]
            session.add_all(
                [
                    SampleTagLinkTable(sample_id=sample_id, tag_id=tag.tag_id)
                    for sample_id in partition
                ]
            )
            start += count
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {split.tag_name: count for split, count in zip(normalized_splits, counts)}


def _validate_splits(splits: Sequence[SplitDefinition]) -> list[SplitDefinition]:
    if len(splits) < _MINIMUM_SPLIT_COUNT:
        raise ValueError("At least two splits are required.")
    normalized = [
        SplitDefinition(tag_name=split.tag_name.strip(), relative_size=split.relative_size)
        for split in splits
    ]
    if any(not split.tag_name for split in normalized):
        raise ValueError("Split tag names must not be blank.")
    if len({split.tag_name for split in normalized}) != len(normalized):
        raise ValueError("Split tag names must be unique.")
    if any(split.relative_size <= 0 for split in normalized):
        raise ValueError("Split relative sizes must be positive.")
    return normalized


def _allocate_counts(sample_count: int, splits: Sequence[SplitDefinition]) -> list[int]:
    total_size = sum(split.relative_size for split in splits)
    quotients_and_remainders = [
        divmod(sample_count * split.relative_size, total_size) for split in splits
    ]
    counts = [quotient for quotient, _ in quotients_and_remainders]
    remaining = sample_count - sum(counts)
    remainders = [remainder for _, remainder in quotients_and_remainders]
    for index in sorted(range(len(splits)), key=lambda index: -remainders[index])[:remaining]:
        counts[index] += 1
    return counts
