"""Matching of query timestamps against the timestamps a topic was recorded at."""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from typing import Callable, NamedTuple, Optional

MatchFunction = Callable[[int, Sequence[int]], Optional[int]]
"""Selects which candidate timestamp matches a query timestamp.

Called as `match(query_ns, candidates_ns)` where `candidates_ns` is sorted in
ascending order. Returns the index of the matching candidate, or `None` for a miss.
"""


class FallbackMatch(NamedTuple):
    """The result of matching on a primary clock, then filling misses from a fallback.

    Attributes:
        indices: One original candidate index per query, or `None` for a miss.
        n_fallback: How many queries were filled from the fallback clock.
    """

    indices: list[int | None]
    n_fallback: int


def closest(max_diff_ns: int | None = None) -> MatchFunction:
    """Returns a match function that picks the candidate closest in time.

    Ties are resolved in favour of the earlier candidate.

    Args:
        max_diff_ns: If given, a candidate further away from the query timestamp than
            this is a miss. Unbounded by default.

    Returns:
        A match function.
    """

    def match(query_ns: int, candidates_ns: Sequence[int]) -> int | None:
        return _closest_index(
            query_ns=query_ns, candidates_ns=candidates_ns, max_diff_ns=max_diff_ns
        )

    return match


def match_all(
    queries_ns: Sequence[int],
    candidates_ns: Sequence[int],
    match: MatchFunction | None = None,
) -> list[int | None]:
    """Matches every query timestamp against the same candidates.

    Use this to pair timestamps that are already in memory, for example the locators of
    two topics read in one pass, instead of reading a topic again.

    Args:
        queries_ns: The query timestamps in nanoseconds.
        candidates_ns: The candidate timestamps in nanoseconds, sorted ascending.
        match: Decides which candidate matches a query timestamp. Defaults to the
            candidate closest in time.

    Returns:
        One entry per query timestamp, in the same order, holding the index of the
        matching candidate or `None` for a miss.
    """
    match_function = closest() if match is None else match
    return [match_function(query_ns, candidates_ns) for query_ns in queries_ns]


def match_all_with_fallback(
    primary_queries_ns: Sequence[int],
    primary_candidates_ns: Sequence[int],
    fallback_queries_ns: Sequence[int],
    fallback_candidates_ns: Sequence[int],
    match: MatchFunction | None = None,
) -> FallbackMatch:
    """Match on the primary clock, then fill misses from the fallback clock.

    Candidate sequences must be the same length and aligned: index i is one candidate
    on both clocks. Query sequences must also be the same length. Each clock is sorted
    independently; returned indices refer to the original candidate order.

    Args:
        primary_queries_ns: The primary query timestamps, e.g. capture times.
        primary_candidates_ns: The primary candidate timestamps, not necessarily sorted.
        fallback_queries_ns: The fallback query timestamps, e.g. log times.
        fallback_candidates_ns: The fallback candidate timestamps, aligned with
            `primary_candidates_ns`.
        match: Decides which candidate matches a query timestamp. Defaults to the
            candidate closest in time.

    Returns:
        The original candidate index of every query, and how many used the fallback.

    Raises:
        ValueError: If a query pair or a candidate pair has unequal length.
    """
    if len(primary_queries_ns) != len(fallback_queries_ns):
        raise ValueError("Primary and fallback query lists must have the same length.")
    if len(primary_candidates_ns) != len(fallback_candidates_ns):
        raise ValueError("Primary and fallback candidate lists must have the same length.")
    match_function = closest() if match is None else match
    primary = _match_original_indices(
        queries_ns=primary_queries_ns,
        candidates_ns=primary_candidates_ns,
        match=match_function,
    )
    if all(index is not None for index in primary):
        return FallbackMatch(indices=primary, n_fallback=0)
    fallback = _match_original_indices(
        queries_ns=fallback_queries_ns,
        candidates_ns=fallback_candidates_ns,
        match=match_function,
    )
    indices: list[int | None] = []
    n_fallback = 0
    for primary_index, fallback_index in zip(primary, fallback):
        if primary_index is not None:
            indices.append(primary_index)
            continue
        indices.append(fallback_index)
        if fallback_index is not None:
            n_fallback += 1
    return FallbackMatch(indices=indices, n_fallback=n_fallback)


def _match_original_indices(
    queries_ns: Sequence[int], candidates_ns: Sequence[int], match: MatchFunction
) -> list[int | None]:
    """Match queries against unsorted candidates and return original indices."""
    order = sorted(range(len(candidates_ns)), key=lambda index: candidates_ns[index])
    sorted_ns = [candidates_ns[index] for index in order]
    matched = match_all(queries_ns=queries_ns, candidates_ns=sorted_ns, match=match)
    return [None if index is None else order[index] for index in matched]


def _closest_index(
    query_ns: int, candidates_ns: Sequence[int], max_diff_ns: int | None
) -> int | None:
    """Returns the index of the candidate closest to the query timestamp.

    Args:
        query_ns: The query timestamp in nanoseconds.
        candidates_ns: The candidate timestamps in nanoseconds, sorted ascending.
        max_diff_ns: The largest accepted distance, or `None` for no bound.

    Returns:
        The index of the closest candidate, or `None` if there is no candidate within
        `max_diff_ns`.
    """
    if not candidates_ns:
        return None

    after = bisect.bisect_left(candidates_ns, query_ns)
    closest_index = min(after, len(candidates_ns) - 1)
    if after > 0 and query_ns - candidates_ns[after - 1] <= abs(
        candidates_ns[closest_index] - query_ns
    ):
        closest_index = after - 1

    if max_diff_ns is not None and abs(candidates_ns[closest_index] - query_ns) > max_diff_ns:
        return None
    return closest_index
