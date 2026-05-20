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


def test_assign_color_categories() -> None:
    ids = [uuid4(), uuid4()]
    scale = DiscreteColorScale.from_values(values=["cat", "dog"])
    sample_to_value = {ids[0]: "cat", ids[1]: "dog"}

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=ids,
        fulfils_filter=[1, 1],
        sample_to_value=sample_to_value,
        scale=scale,
    )

    assert legend == {0: "Filtered out", 1: "Unassigned", 2: "cat", 3: "dog"}
    assert categories == [2, 3]


def test_assign_color_categories__missing_and_filtered_out() -> None:
    ids = [uuid4(), uuid4()]
    scale = DiscreteColorScale.from_values(values=["cat"])
    sample_to_value = {ids[0]: "cat"}  # ids[1] is missing

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=ids,
        fulfils_filter=[0, 1],
        sample_to_value=sample_to_value,
        scale=scale,
    )

    assert legend == {0: "Filtered out", 1: "Unassigned", 2: "cat"}
    assert categories == [0, 1]


def test_assign_color_categories__mixed() -> None:
    """Filtered-out, valued, and missing samples in one call."""
    ids = [uuid4(), uuid4(), uuid4(), uuid4()]
    scale = DiscreteColorScale.from_values(values=["London", "Paris"])
    sample_to_value: dict[UUID, str] = {
        ids[0]: "Paris",
        ids[1]: "London",
        # ids[2] has no value
        ids[3]: "Paris",
    }

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=ids,
        fulfils_filter=[1, 0, 1, 1],
        sample_to_value=sample_to_value,
        scale=scale,
    )

    # Legend includes reserved entries + scale entries
    assert legend == {0: "Filtered out", 1: "Unassigned", 2: "London", 3: "Paris"}
    assert categories == [3, 0, 1, 3]


def test_assign_color_categories__empty() -> None:
    scale = DiscreteColorScale.from_values(values=["x"])

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=[],
        fulfils_filter=[],
        sample_to_value={},
        scale=scale,
    )

    assert legend == {0: "Filtered out", 1: "Unassigned", 2: "x"}
    assert categories == []


def test_assign_color_categories__unmapped_value() -> None:
    """A sample whose value exists but isn't in the scale gets category 1."""
    sid = uuid4()
    scale = DiscreteColorScale.from_values(values=["known"])

    categories, legend = coloring_helpers.assign_color_categories(
        sample_ids=[sid],
        fulfils_filter=[1],
        sample_to_value={sid: "unknown"},
        scale=scale,
    )

    assert legend == {0: "Filtered out", 1: "Unassigned", 2: "known"}
    assert categories == [1]
