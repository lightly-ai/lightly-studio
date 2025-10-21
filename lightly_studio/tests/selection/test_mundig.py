from __future__ import annotations

import numpy as np
import pytest
from pytest_mock import MockerFixture

from lightly_studio.selection.mundig import Mundig


class TestMundig:
    """Tests for the interface from python to mundig.

    Testing that the algorithms work is NOT required here, this only
    tests the interface.
    """

    def test_diversity(self) -> None:
        """Test the diversity strategy."""
        mundig = Mundig()
        mundig.add_diversity([[1], [3], [5]])
        selected = mundig.run(n_samples=2)
        assert selected == [0, 2]

    def test_diversity__pass_ndarray(self) -> None:
        """Test the diversity strategy with ndarray float64 input."""
        mundig = Mundig()
        mundig.add_diversity(np.array([[1], [3], [5]], dtype=np.float64))
        selected = mundig.run(n_samples=2)
        assert selected == [0, 2]

    def test_diversity__pass_ndarray_zero_copy(self, mocker: MockerFixture) -> None:
        """Test that there is no ndarray copy if it already is np.float32.

        Does so by spying on np.array() and asserting that it was not called.
        """
        mundig = Mundig()
        embeddings = np.array([[1], [3], [5]], dtype=np.float32)
        spy_np_array = mocker.spy(np, "array")
        mundig.add_diversity(embeddings)
        spy_np_array.assert_not_called()

    def test_diversity__differing_embedding_sizes(self) -> None:
        """Check error is raised if embedding sizes differ."""
        mundig = Mundig()
        with pytest.raises(
            ValueError,
            match=(
                "setting an array element with a sequence. "
                "The requested array has an inhomogeneous shape after "
                "1 dimensions. "
            ),
        ):
            mundig.add_diversity([[1], [3, 4], [5]])

    def test_weighting(self) -> None:
        """Test the weighting strategy."""
        mundig = Mundig()
        mundig.add_weighting([1, 2, 3])
        selected = mundig.run(n_samples=2)
        assert selected == [2, 1]

    def test_weighting__multiple(self) -> None:
        """Test the weighting strategy with multiple calls."""
        mundig = Mundig()
        mundig.add_weighting([1, 2, 3])
        mundig.add_weighting([6, 5, 3])
        selected = mundig.run(n_samples=2)
        assert selected == [1, 2]

    def test_multiple__wrong_n_input_samples(self) -> None:
        """Check error is raised if input sample sizes differ."""
        mundig = Mundig()
        mundig.add_diversity([[1, 2], [3, 4]])
        with pytest.raises(
            ValueError,
            match=("Expected 2 input samples, but the latest strategy passed 3\\."),
        ):
            mundig.add_weighting([1, 2, 3])

    def test_class_balancing(self) -> None:
        """Test the class balancing strategy."""
        mundig = Mundig()
        # 5 samples, 2 classes
        class_distributions = [[1.0, 0.0], [0.3, 0.7], [0.0, 1.0], [0.0, 1.0], [1.0, 1.0]]
        mundig.add_class_balancing(class_distributions=class_distributions, target=[0.5, 0.5])
        selected = mundig.run(n_samples=2)

        # Sample at index 4 with distribution [1.0, 1.0] is perfectly in balance with the target of
        # 50:50. Then sample at index 1 with distribution [0.3, 0.7] is the closest to 50:50.
        assert selected == [4, 1]

    def test_class_balancing_wrong_dimensions(self) -> None:
        """Test class balancing with wrong dimensions."""
        mundig = Mundig()
        # Uneven lengths of rows
        class_distributions = [[1.0, 0.0], [0.3]]
        with pytest.raises(
            ValueError, match="The requested array has an inhomogeneous shape after 1 dimensions"
        ):
            mundig.add_class_balancing(class_distributions=class_distributions, target=[0.5, 0.5])

    def test_class_balancing_nonmatching_length(self) -> None:
        """Test class balancing with target length not matching class_distributions columns."""
        mundig = Mundig()
        # 2 classes
        class_distributions = [[1.0, 0.0], [0.3, 0.7]]
        with pytest.raises(
            ValueError,
            match="The length of 'target' 1 doesn't match the width of 'class_distributions': 2",
        ):
            # `target` only has 1 class
            mundig.add_class_balancing(class_distributions=class_distributions, target=[0.5])

    def test_mundig_rust_error(self) -> None:
        """Test the error handling for Rust exceptions.

        Passes 2 samples in a weighting strategy, but tells that there
        are 3 samples.
        """
        mundig = Mundig()
        mundig.mundig.add_weighting_strategy([1, 2], strength=3)
        # Only BaseException works, as the exception comes from Rust.
        # Full error: "pyo3_runtime.PanicException: called `Result::unwrap()` on
        #  an `Err` value: ShapeError/IncompatibleShape: incompatible shapes"
        with pytest.raises(BaseException, match="ShapeError/IncompatibleShape"):
            mundig.mundig.run_selection(n_total_samples=3, n_samples_to_select=1)
