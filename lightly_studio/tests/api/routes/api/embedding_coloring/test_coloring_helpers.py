"""Unit tests for the coloring_helpers module."""

from __future__ import annotations

from uuid import UUID, uuid4

from lightly_studio.api.routes.api.embedding_coloring import coloring_helpers
from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import DiscreteColorScale


class TestDiscreteColorScale:
    """Tests for DiscreteColorScale."""

    def test_value_to_category__known_value(self) -> None:
        scale = DiscreteColorScale(_lookup={"a": 2, "b": 3}, legend={2: "a", 3: "b"})
        assert scale.value_to_category("a") == 2
        assert scale.value_to_category("b") == 3
        assert scale.value_to_category("z") is None

    def test_from_values__strings(self) -> None:
        scale = DiscreteColorScale.from_values(values=["Berlin", "London", "Paris"])
        assert scale.value_to_category("Berlin") == 2
        assert scale.value_to_category("London") == 3
        assert scale.value_to_category("Paris") == 4
        assert scale.legend == {2: "Berlin", 3: "London", 4: "Paris"}

    def test_from_values__booleans(self) -> None:
        scale = DiscreteColorScale.from_values(
            values=[False, True],
            format_fn=lambda v: str(v).lower(),
        )
        # Sorted by format_fn: "false" < "true"
        assert scale.value_to_category(False) == 2
        assert scale.value_to_category(True) == 3
        assert scale.legend == {2: "false", 3: "true"}

    def test_from_values__custom_start_cat(self) -> None:
        scale = DiscreteColorScale.from_values(values=["x", "y"], start_cat=10)
        assert scale.value_to_category("x") == 10
        assert scale.value_to_category("y") == 11
        assert scale.legend == {10: "x", 11: "y"}

    def test_from_values__empty(self) -> None:
        scale = DiscreteColorScale[str].from_values(values=[])
        assert scale.legend == {}
        assert scale.value_to_category("anything") is None

    def test_from_values__single_value(self) -> None:
        scale = DiscreteColorScale.from_values(values=["only"])
        assert scale.value_to_category("only") == 2
        assert scale.legend == {2: "only"}

    def test_from_values__exactly_fits_all_listed(self) -> None:
        # 254 values fit in slots [2, 256): every value keeps its own category.
        values = [f"v{i:03d}" for i in range(254)]
        scale = DiscreteColorScale.from_values(values=values)
        assert len(scale.legend) == 254
        assert scale.value_to_category("v000") == 2
        assert scale.value_to_category("v253") == 255
        assert scale.legend[255] == "v253"
        assert all(not label.startswith("Other") for label in scale.legend.values())

    def test_from_values__overflow_groups_into_other(self) -> None:
        # 256 values exceed the 254 slots: 253 are listed, the rest go to "Other".
        values = [f"v{i:03d}" for i in range(256)]
        scale = DiscreteColorScale.from_values(values=values)
        # 253 individual categories (slots 2..254) + the "Other" slot 255.
        assert len(scale.legend) == 254
        assert scale.value_to_category("v000") == 2
        assert scale.value_to_category("v252") == 254
        # Everything from the 254th value onward collapses into the final slot.
        assert scale.value_to_category("v253") == 255
        assert scale.value_to_category("v254") == 255
        assert scale.value_to_category("v255") == 255
        # The "Other" label lists the first few grouped names then truncates.
        assert scale.legend[255] == "Other (v253, v254, v255)"

    def test_from_values__overflow_other_label_truncated(self) -> None:
        values = [f"v{i:03d}" for i in range(260)]
        scale = DiscreteColorScale.from_values(values=values)
        # More grouped values than MAX_OTHER_NAMES -> ellipsis appended.
        assert scale.legend[255] == "Other (v253, v254, v255, v256, v257, …)"

    def test_from_integers__few_values(self) -> None:
        scale = DiscreteColorScale.from_integers(values=[3, 1, 2])
        assert scale.value_to_category(1) == 2
        assert scale.value_to_category(2) == 3
        assert scale.value_to_category(3) == 4
        assert scale.legend == {2: "1", 3: "2", 4: "3"}

    def test_from_integers__empty(self) -> None:
        scale = DiscreteColorScale.from_integers(values=[])
        assert scale.legend == {}
        assert scale.value_to_category(0) is None

    def test_from_integers__duplicates_deduplicated(self) -> None:
        scale = DiscreteColorScale.from_integers(values=[5, 5, 3, 3, 1])
        assert scale.value_to_category(1) == 2
        assert scale.value_to_category(3) == 3
        assert scale.value_to_category(5) == 4
        assert scale.legend == {2: "1", 3: "3", 4: "5"}

    def test_from_integers__custom_start_cat(self) -> None:
        scale = DiscreteColorScale.from_integers(values=[10, 20], start_cat=5)
        assert scale.value_to_category(10) == 5
        assert scale.value_to_category(20) == 6
        assert scale.legend == {5: "10", 6: "20"}

    def test_from_integers__exactly_max_categories_no_bucketing(self) -> None:
        scale = DiscreteColorScale.from_integers(values=[1, 2, 3], max_categories=3)
        assert scale.value_to_category(1) == 2
        assert scale.value_to_category(2) == 3
        assert scale.value_to_category(3) == 4
        assert scale.legend == {2: "1", 3: "2", 4: "3"}

    def test_from_integers__bucketing(self) -> None:
        # value_range=300, raw_width=150, magnitude=100, bucket_width=200
        # -> 2 buckets: [0, 199] and [200, 399]
        scale = DiscreteColorScale.from_integers(values=[0, 100, 200, 300], max_categories=2)
        assert scale.value_to_category(0) == 2
        assert scale.value_to_category(100) == 2
        assert scale.value_to_category(200) == 3
        assert scale.value_to_category(300) == 3
        assert scale.legend == {2: "0-199", 3: "200-399"}

    def test_from_integers__bucketing_width_one(self) -> None:
        scale = DiscreteColorScale.from_integers(values=[0, 1, 2], max_categories=2)
        assert scale.value_to_category(0) == 2
        assert scale.value_to_category(1) == 3
        assert scale.value_to_category(2) == 4
        assert scale.legend == {2: "0", 3: "1", 4: "2"}


def test_assign_color_categories() -> None:
    ids = [uuid4(), uuid4()]
    scale = DiscreteColorScale.from_values(values=["cat", "dog"])
    sample_to_values = {ids[0]: ["cat"], ids[1]: ["dog"]}

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=ids,
        sample_to_values=sample_to_values,
        scale=scale,
    )

    # No reserved entries: the legend only describes the color scale.
    assert legend == {2: "cat", 3: "dog"}
    assert categories == [[2], [3]]


def test_assign_color_categories__multiple_values_sorted_by_category() -> None:
    """A sample with several values gets all categories, sorted ascending."""
    sid = uuid4()
    scale = DiscreteColorScale.from_values(values=["cat", "dog", "fish"])

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=[sid],
        # Values out of order; the output is sorted by color category.
        sample_to_values={sid: {"fish", "dog"}},
        scale=scale,
    )

    assert legend == {2: "cat", 3: "dog", 4: "fish"}
    assert categories == [[3, 4]]


def test_assign_color_categories__missing_value_is_empty() -> None:
    ids = [uuid4(), uuid4()]
    scale = DiscreteColorScale.from_values(values=["cat"])
    sample_to_values = {ids[0]: ["cat"]}  # ids[1] is missing

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=ids,
        sample_to_values=sample_to_values,
        scale=scale,
    )

    assert legend == {2: "cat"}
    # Samples without a value map to an empty list; the filter/unassigned
    # reserved categories are assigned downstream.
    assert categories == [[2], []]


def test_assign_color_categories__mixed() -> None:
    """Valued, multi-valued, and missing samples in one call."""
    ids = [uuid4(), uuid4(), uuid4()]
    scale = DiscreteColorScale.from_values(values=["London", "Paris"])
    sample_to_values: dict[UUID, list[str]] = {
        ids[0]: ["Paris"],
        # ids[1] has no value
        ids[2]: ["Paris", "London"],
    }

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=ids,
        sample_to_values=sample_to_values,
        scale=scale,
    )

    assert legend == {2: "London", 3: "Paris"}
    assert categories == [[3], [], [2, 3]]


def test_assign_color_categories__empty() -> None:
    scale = DiscreteColorScale.from_values(values=["x"])

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=[],
        sample_to_values={},
        scale=scale,
    )

    assert legend == {2: "x"}
    assert categories == []


def test_assign_color_categories__unmapped_value_is_empty() -> None:
    """A sample whose value exists but isn't in the scale gets an empty list."""
    sid = uuid4()
    scale = DiscreteColorScale.from_values(values=["known"])

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=[sid],
        sample_to_values={sid: ["unknown"]},
        scale=scale,
    )

    assert legend == {2: "known"}
    assert categories == [[]]


def test_order_values_by_frequency() -> None:
    ids = [uuid4() for _ in range(4)]
    sample_to_values = {
        ids[0]: ["a"],
        ids[1]: ["b"],
        ids[2]: ["b"],
        ids[3]: ["b", "c"],
    }
    ordered = coloring_helpers.order_values_by_frequency(
        sample_to_values=sample_to_values,
        matching_sample_ids=None,
    )
    # "b" in 3 samples, "a"/"c" in 1 each (tie broken alphabetically).
    assert ordered == ["b", "a", "c"]


def test_order_values_by_frequency__tie_broken_by_formatted_label() -> None:
    ids = [uuid4(), uuid4()]
    sample_to_values = {ids[0]: [2], ids[1]: [10]}
    # As integers 2 < 10, but the formatted labels sort "10" < "2".
    ordered = coloring_helpers.order_values_by_frequency(
        sample_to_values=sample_to_values,
        matching_sample_ids=None,
    )
    assert ordered == [10, 2]


def test_order_values_by_frequency__mask_restricts_and_omits_absent_values() -> None:
    ids = [uuid4() for _ in range(3)]
    sample_to_values = {
        ids[0]: ["kept"],
        ids[1]: ["kept"],
        ids[2]: ["dropped"],
    }
    # Only the first two samples match; "dropped" never occurs among them.
    ordered = coloring_helpers.order_values_by_frequency(
        sample_to_values=sample_to_values,
        matching_sample_ids={ids[0], ids[1]},
    )
    assert ordered == ["kept"]


def test_order_values_by_frequency__value_counts_once_per_sample() -> None:
    sid, other = uuid4(), uuid4()
    sample_to_values = {sid: ["dup", "dup"], other: ["single"]}
    ordered = coloring_helpers.order_values_by_frequency(
        sample_to_values=sample_to_values,
        matching_sample_ids=None,
    )
    # "dup" repeats within one sample but counts once -> tie, broken by label.
    assert ordered == ["dup", "single"]
