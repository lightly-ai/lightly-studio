"""The agent tool that shows how samples spread over metadata values and annotation classes.

Each distribution is a list of entries with a ``count`` and a ``share``. A categorical
metadata key has one entry per value, a numeric key one entry per bin, a date key one
entry per year, and the annotation classes one entry per class.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from lightly_studio.agent import sample_source
from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.metadata import CATEGORICAL_TYPE_NAMES, NUMERIC_TYPE_NAMES
from lightly_studio.resolvers import image_resolver, metadata_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode
from lightly_studio.resolvers.metadata_resolver.sample import (
    categorical_value_counts,
    get_metadata_info,
    metadata_helpers,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

# The number of most frequent values or classes that a distribution lists. The other values
# are counted together in one `__other__` entry.
_MAX_LISTED_VALUES = 20

# The number of equal-width bins for a numeric metadata key.
_BIN_COUNT = 10

# The entries that count the samples without a value, and the less frequent values. The
# names are the same as in `categorical_value_counts`.
_MISSING = "__missing__"
_OTHER = "__other__"


class GetDistributionArgs(BaseModel):
    """Arguments of ``get_distribution``."""

    metadata_keys: list[str] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "Metadata keys from get_collection_overview. A string or boolean key gives the "
            "count per value. A numeric key gives the count per value range."
        ),
    )
    year_keys: list[str] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "String metadata keys with dates that start with the year, such as '2025-06-30' "
            "or '2025-06-30T12:00:00'. Gives the count per year."
        ),
    )
    annotation_classes: bool = Field(
        default=False,
        description=(
            "True gives the number of samples with each annotation class. A sample with "
            "several classes counts for each of them."
        ),
    )
    source: str = Field(
        default="all", description="The samples to count. " + sample_source.SOURCE_DESCRIPTION
    )


def get_distribution(context: AgentContext, args: GetDistributionArgs) -> dict[str, Any]:
    """Count the samples of the source per metadata value, year and annotation class."""
    if not args.metadata_keys and not args.year_keys and not args.annotation_classes:
        raise ValueError("Give at least one metadata key, year key or annotation_classes=true.")
    source = args.source.strip()
    sample_ids = None if source == "all" else sample_source.resolve_source(context, source)
    sample_count = _count_samples(context=context, sample_ids=sample_ids)
    result: dict[str, Any] = {"sample_count": sample_count}
    if args.metadata_keys:
        result["metadata"] = get_metadata_distributions(
            context=context, sample_ids=sample_ids, keys=args.metadata_keys
        )
    if args.year_keys:
        result["years"] = {
            key: _get_year_distribution(
                context=context, sample_ids=sample_ids, key=key, sample_count=sample_count
            )
            for key in dict.fromkeys(args.year_keys)
        }
    if args.annotation_classes:
        result["annotation_classes"] = get_annotation_class_distribution(
            context=context, sample_ids=sample_ids, count_mode=AnnotationCountMode.SAMPLES
        )
    return result


DISTRIBUTION_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name="get_distribution",
        description=(
            "Count how many samples have each metadata value, each year of a date key, or "
            "each annotation class. Works on all samples, a tag, the GUI selection or a "
            "result. Use it for questions about the distribution of the data, instead of "
            "one find_samples call per value. The entry '__other__' groups the less "
            "frequent values. The entry '__missing__' counts the samples without a value."
        ),
        args_model=GetDistributionArgs,
        run=get_distribution,
    ),
]


def get_metadata_distributions(
    context: AgentContext, sample_ids: Sequence[UUID] | None, keys: Sequence[str]
) -> dict[str, list[dict[str, Any]]]:
    """Count the samples per value of categorical keys and per value range of numeric keys.

    Args:
        context: The context of the turn.
        sample_ids: The samples to count. None counts all samples of the collection.
        keys: The metadata keys.

    Returns:
        A mapping from each key to its entries. A categorical key lists its values, the most
        frequent first. A numeric key lists its bins in order, each with ``min`` and ``max``.

    Raises:
        ValueError: If a key is not a categorical or numeric metadata key of the collection.
    """
    session = context.session
    collection_id = context.collection.collection_id
    schema = metadata_helpers.get_merged_schema(session=session, collection_id=collection_id)
    keys = list(dict.fromkeys(keys))
    unknown_keys = [
        key for key in keys if schema.get(key) not in (*CATEGORICAL_TYPE_NAMES, *NUMERIC_TYPE_NAMES)
    ]
    if unknown_keys:
        raise ValueError(
            f"These keys are not string, boolean or numeric metadata keys: {unknown_keys}. "
            "Use the keys from get_collection_overview."
        )
    filters = _to_filter(sample_ids=sample_ids)
    categorical_keys = [key for key in keys if schema[key] in CATEGORICAL_TYPE_NAMES]
    numeric_keys = [key for key in keys if schema[key] in NUMERIC_TYPE_NAMES]
    value_counts = (
        categorical_value_counts.get_metadata_value_counts(
            session=session,
            collection_id=collection_id,
            filters=filters,
            fields=categorical_keys,
            limit=_MAX_LISTED_VALUES,
        )
        if categorical_keys
        else {}
    )
    histograms = (
        get_metadata_info.get_metadata_histograms(
            session=session,
            collection_id=collection_id,
            filters=filters,
            bin_count=_BIN_COUNT,
            fields=numeric_keys,
        )
        if numeric_keys
        else {}
    )
    sample_count = _count_samples(context=context, sample_ids=sample_ids)
    distributions = {}
    for key in keys:
        entries: list[dict[str, Any]]
        if key in value_counts:
            entries = [
                {"value": count.value, "count": count.count}
                for count in value_counts[key].value_counts
            ]
        else:
            histogram = histograms[key]
            entries = [
                {"min": round(low, 3), "max": round(high, 3), "count": count}
                for low, high, count in zip(
                    histogram.bin_edges, histogram.bin_edges[1:], histogram.counts
                )
            ]
            _append_missing(entries=entries, sample_count=sample_count)
        distributions[key] = _with_shares(entries=entries, total=sample_count)
    return distributions


def get_annotation_class_distribution(
    context: AgentContext, sample_ids: Sequence[UUID] | None, count_mode: AnnotationCountMode
) -> list[dict[str, Any]]:
    """Count the samples or the annotations of each annotation class.

    Args:
        context: The context of the turn.
        sample_ids: The samples to count. None counts all samples of the collection.
        count_mode: ``SAMPLES`` counts the samples with each class, and the share is of all
            samples. ``OBJECTS`` counts the annotations of each class, and the share is of
            all annotations.

    Returns:
        The classes, the most frequent first, with an ``__other__`` entry for the classes
        after the first ``_MAX_LISTED_VALUES``.
    """
    counts = image_resolver.count_image_annotations_by_collection(
        session=context.session,
        collection_id=context.collection.collection_id,
        image_filter=_to_filter(sample_ids=sample_ids),
        count_mode=count_mode,
    )
    rows = sorted(
        ((name, current) for name, current, _ in counts if current > 0),
        key=lambda row: (-row[1], row[0]),
    )
    entries: list[dict[str, Any]] = [
        {"value": name, "count": count} for name, count in rows[:_MAX_LISTED_VALUES]
    ]
    other_count = sum(count for _, count in rows[_MAX_LISTED_VALUES:])
    if other_count:
        entries.append({"value": _OTHER, "count": other_count})
    total = (
        _count_samples(context=context, sample_ids=sample_ids)
        if count_mode == AnnotationCountMode.SAMPLES
        else sum(count for _, count in rows)
    )
    return _with_shares(entries=entries, total=total)


def _get_year_distribution(
    context: AgentContext, sample_ids: Sequence[UUID] | None, key: str, sample_count: int
) -> list[dict[str, Any]]:
    """Count the samples per year of a date string key, the earliest year first.

    A value that does not start with four digits counts as ``__other__``.

    Raises:
        ValueError: If the key is not a string metadata key of the collection.
    """
    values, metadata_type = metadata_resolver.get_metadata_values_for_key(
        session=context.session,
        collection_id=context.collection.collection_id,
        key=key,
        sample_ids=sample_ids,
    )
    if metadata_type != "string":
        raise ValueError(f"The key {key!r} is not a string metadata key, so it has no dates.")
    years = Counter(value[:4] if value[:4].isdigit() else _OTHER for value in values.values())
    entries: list[dict[str, Any]] = [
        {"value": year, "count": years[year]} for year in sorted(years.keys() - {_OTHER})
    ]
    if years[_OTHER]:
        entries.append({"value": _OTHER, "count": years[_OTHER]})
    _append_missing(entries=entries, sample_count=sample_count)
    return _with_shares(entries=entries, total=sample_count)


def _count_samples(context: AgentContext, sample_ids: Sequence[UUID] | None) -> int:
    if sample_ids is not None:
        return len(sample_ids)
    return image_resolver.get_all_by_collection_id(
        session=context.session,
        collection_id=context.collection.collection_id,
        pagination=Paginated(offset=0, limit=1),
    ).total_count


def _to_filter(sample_ids: Sequence[UUID] | None) -> ImageFilter | None:
    """Restrict a resolver to the samples. None does not restrict it."""
    if sample_ids is None:
        return None
    return ImageFilter(sample_filter=SampleFilter(sample_ids=list(sample_ids)))


def _append_missing(entries: list[dict[str, Any]], sample_count: int) -> None:
    """Add a ``__missing__`` entry for the samples that the entries do not count."""
    missing_count = sample_count - sum(entry["count"] for entry in entries)
    if missing_count > 0:
        entries.append({"value": _MISSING, "count": missing_count})


def _with_shares(entries: list[dict[str, Any]], total: int) -> list[dict[str, Any]]:
    return [
        {**entry, "share": round(entry["count"] / total, 3) if total else 0.0} for entry in entries
    ]
