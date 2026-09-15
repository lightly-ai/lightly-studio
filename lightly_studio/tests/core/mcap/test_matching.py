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
