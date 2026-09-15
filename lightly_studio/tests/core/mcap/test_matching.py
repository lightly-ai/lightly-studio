from __future__ import annotations

from lightly_studio.core.mcap import matching

CANDIDATES_NS = [100, 200, 400]


def test_closest() -> None:
    match = matching.closest()
    assert match(100, CANDIDATES_NS) == 0
    assert match(179, CANDIDATES_NS) == 1
    assert match(500, CANDIDATES_NS) == 2


def test_closest__before_first_candidate() -> None:
    match = matching.closest()
    assert match(1, CANDIDATES_NS) == 0


def test_closest__tie_picks_earlier_candidate() -> None:
    match = matching.closest()
    assert match(150, CANDIDATES_NS) == 0


def test_closest__no_candidates() -> None:
    match = matching.closest()
    assert match(100, []) is None


def test_closest__within_max_diff() -> None:
    match = matching.closest(max_diff_ns=20)
    assert match(210, CANDIDATES_NS) == 1


def test_closest__outside_max_diff() -> None:
    match = matching.closest(max_diff_ns=20)
    assert match(250, CANDIDATES_NS) is None
    assert match(1_000, CANDIDATES_NS) is None
    assert match(0, CANDIDATES_NS) is None


def test_match_all() -> None:
    assert matching.match_all(queries_ns=[100, 179, 500], candidates_ns=CANDIDATES_NS) == [0, 1, 2]


def test_match_all__with_match_function() -> None:
    indices = matching.match_all(
        queries_ns=[210, 250],
        candidates_ns=CANDIDATES_NS,
        match=matching.closest(max_diff_ns=20),
    )
    assert indices == [1, None]


def test_match_all__no_queries() -> None:
    assert matching.match_all(queries_ns=[], candidates_ns=CANDIDATES_NS) == []


def test_match_all__no_candidates() -> None:
    assert matching.match_all(queries_ns=[100, 200], candidates_ns=[]) == [None, None]
