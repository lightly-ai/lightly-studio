"""Matching of query timestamps against the timestamps a topic was recorded at."""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from typing import Callable, Optional

MatchFunction = Callable[[int, Sequence[int]], Optional[int]]
"""Selects which candidate timestamp matches a query timestamp.

Called as `match(query_ns, candidates_ns)` where `candidates_ns` is sorted in
ascending order. Returns the index of the matching candidate, or `None` for a miss.
"""


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
