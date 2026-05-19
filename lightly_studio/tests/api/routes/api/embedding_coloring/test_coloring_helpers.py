"""Unit tests for the coloring_helpers module."""

from __future__ import annotations

from uuid import UUID, uuid4

from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import (
    DiscreteColorScale,
    assign_color_categories,
)


class TestDiscreteColorScale:
    """Tests for DiscreteColorScale."""

    def test_value_to_category__known_value(self) -> None:
        scale = DiscreteColorScale(_lookup={"a": 2, "b": 3}, legend={2: "a", 3: "b"})
        assert scale.value_to_category("a") == 2
        assert scale.value_to_category("b") == 3

    def test_value_to_category__unknown_value(self) -> None:
        scale = DiscreteColorScale(_lookup={"a": 2}, legend={2: "a"})
        assert scale.value_to_category("z") is None

    def test_from_values__strings(self) -> None:
        scale = DiscreteColorScale.from_values(values={"Paris", "London", "Berlin"})
        assert scale.value_to_category("Berlin") == 2
        assert scale.value_to_category("London") == 3
        assert scale.value_to_category("Paris") == 4
        assert scale.legend == {2: "Berlin", 3: "London", 4: "Paris"}

    def test_from_values__booleans(self) -> None:
        scale = DiscreteColorScale.from_values(
            values={True, False},
            format_fn=lambda v: str(v).lower(),
        )
        # Sorted by format_fn: "false" < "true"
        assert scale.value_to_category(False) == 2
        assert scale.value_to_category(True) == 3
        assert scale.legend == {2: "false", 3: "true"}

    def test_from_values__custom_start_cat(self) -> None:
        scale = DiscreteColorScale.from_values(values={"x", "y"}, start_cat=10)
        assert scale.value_to_category("x") == 10
        assert scale.value_to_category("y") == 11
        assert scale.legend == {10: "x", 11: "y"}

    def test_from_values__empty(self) -> None:
        scale = DiscreteColorScale.from_values(values=set())
        assert scale.legend == {}
        assert scale.value_to_category("anything") is None

    def test_from_values__single_value(self) -> None:
        scale = DiscreteColorScale.from_values(values={"only"})
        assert scale.value_to_category("only") == 2
        assert scale.legend == {2: "only"}

    def test_from_values__deterministic_ordering(self) -> None:
        """Repeated calls with the same values produce the same assignment."""
        for _ in range(5):
            scale = DiscreteColorScale.from_values(values={"c", "a", "b"})
            assert scale.legend == {2: "a", 3: "b", 4: "c"}


class TestAssignColorCategories:
    """Tests for assign_color_categories."""

    def test_all_samples_have_values(self) -> None:
        ids = [uuid4(), uuid4()]
        scale = DiscreteColorScale.from_values(values={"cat", "dog"})
        sample_to_value = {ids[0]: "cat", ids[1]: "dog"}

        categories, legend = assign_color_categories(
            sample_ids=ids,
            fulfils_filter=[1, 1],
            sample_to_value=sample_to_value,
            scale=scale,
        )

        assert categories[0] == scale.value_to_category("cat")
        assert categories[1] == scale.value_to_category("dog")
        assert legend[0] == "Filtered out"
        assert legend[1] == "Unassigned"

    def test_filtered_out_sample_gets_category_zero(self) -> None:
        sid = uuid4()
        scale = DiscreteColorScale.from_values(values={"val"})

        categories, _ = assign_color_categories(
            sample_ids=[sid],
            fulfils_filter=[0],
            sample_to_value={sid: "val"},
            scale=scale,
        )

        assert categories == [0]

    def test_missing_value_gets_unassigned(self) -> None:
        sid = uuid4()
        scale = DiscreteColorScale.from_values(values={"val"})

        categories, legend = assign_color_categories(
            sample_ids=[sid],
            fulfils_filter=[1],
            sample_to_value={},
            scale=scale,
        )

        assert categories == [1]
        assert legend[1] == "Unassigned"

    def test_mixed_scenario(self) -> None:
        """Filtered-out, valued, and missing samples in one call."""
        ids = [uuid4(), uuid4(), uuid4(), uuid4()]
        scale = DiscreteColorScale.from_values(values={"Paris", "London"})
        sample_to_value: dict[UUID, str] = {
            ids[0]: "Paris",
            ids[1]: "London",
            # ids[2] has no value
            ids[3]: "Paris",
        }

        categories, legend = assign_color_categories(
            sample_ids=ids,
            fulfils_filter=[1, 0, 1, 1],
            sample_to_value=sample_to_value,
            scale=scale,
        )

        assert categories[0] == scale.value_to_category("Paris")  # valued
        assert categories[1] == 0  # filtered out
        assert categories[2] == 1  # unassigned (missing)
        assert categories[3] == scale.value_to_category("Paris")  # valued

        # Legend includes reserved entries + scale entries
        assert legend[0] == "Filtered out"
        assert legend[1] == "Unassigned"
        assert "London" in legend.values()
        assert "Paris" in legend.values()

    def test_empty_samples(self) -> None:
        scale = DiscreteColorScale.from_values(values={"x"})

        categories, legend = assign_color_categories(
            sample_ids=[],
            fulfils_filter=[],
            sample_to_value={},
            scale=scale,
        )

        assert categories == []
        assert legend[0] == "Filtered out"
        assert legend[1] == "Unassigned"

    def test_unmapped_value_in_scale_gets_unassigned(self) -> None:
        """A sample whose value exists but isn't in the scale gets category 1."""
        sid = uuid4()
        scale = DiscreteColorScale.from_values(values={"known"})

        categories, _ = assign_color_categories(
            sample_ids=[sid],
            fulfils_filter=[1],
            sample_to_value={sid: "unknown"},
            scale=scale,
        )

        assert categories == [1]
