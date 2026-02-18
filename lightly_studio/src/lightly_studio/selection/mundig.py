"""Python interface to the Mundig selection algorithm."""

from __future__ import annotations

from typing import Iterable

# TODO(Malte, 08/2025): About the type ignore:
# Use pyo3 typing stubs once they are implemented.
# See https://github.com/PyO3/pyo3/issues/510
# Or remove the type ignore once typing stubs were added manually.
import lightly_mundig  # type: ignore[import-untyped]
import numpy as np

from lightly_studio.dataset.env import LIGHTLY_STUDIO_LICENSE_KEY


class Mundig:
    """Python interface for the Mundig selection algorithm.

    This class provides a Python interface to the lightly_mundig Rust library
    for sample selection. It allows combining different selection strategies
    such as diversity and weighting.
    """

    def __init__(self) -> None:
        """Initialize the Mundig selection interface."""
        if LIGHTLY_STUDIO_LICENSE_KEY is None:
            raise ValueError(
                "LIGHTLY_STUDIO_LICENSE_KEY environment variable is not set. "
                "Please set it to your LightlyStudio license key."
            )
        self.mundig = lightly_mundig.Selection(token=LIGHTLY_STUDIO_LICENSE_KEY)

        self.n_input_samples: int | None = None

    def run(self, n_samples: int) -> list[int]:
        """Run the selection algorithm and return selected sample indices.

        Args:
            n_samples: The number of samples to select.

        Returns:
            A list of indices of the selected samples.
        """
        selected: list[int] = self.mundig.run_selection(
            n_total_samples=self.n_input_samples, n_samples_to_select=n_samples
        )
        return selected

    def add_diversity(self, embeddings: Iterable[Iterable[float]], strength: float = 1.0) -> None:
        """Add diversity-based selection using sample embeddings.

        Args:
            embeddings:
                The embeddings of each sample.
                First dimension is over the samples, the second dimension is
                the embedding size. The embedding size must be the same for
                all samples.
            strength:
                The strength of the diversity strategy.

        """
        # Convert to ndarray with float32 dtype if not already
        if isinstance(embeddings, np.ndarray) and embeddings.dtype == np.float32:
            embeddings_ndarray = embeddings
        else:
            embeddings_ndarray = np.array(embeddings, dtype=np.float32)
        self._check_consistent_input_size(embeddings_ndarray.shape[0])
        self.mundig.add_diversifying_strategy(embeddings=embeddings_ndarray, strength=strength)

    def add_weighting(self, weights: Iterable[float], strength: float = 1.0) -> None:
        """Add a weighting strategy.

        Args:
            weights:
                The weight or importance or utility of each sample.
            strength:
                The strength of the weighting strategy.
        """
        weights_ndarray = np.array(weights, dtype=np.float32)
        self._check_consistent_input_size(weights_ndarray.shape[0])
        self.mundig.add_weighting_strategy(weights=weights_ndarray, strength=strength)

    def add_class_balancing(
        self,
        class_distributions: Iterable[Iterable[float]],
        target: Iterable[float],
        strength: float = 1.0,
    ) -> None:
        """Add a class balancing strategy.

        This strategy aims to select a subset of samples such that the
        distribution of classes in the subset is close to the target
        distribution.

        Args:
            class_distributions:
                First dimension is over all samples, second one is the distribution per sample over
                the classes.
            target:
                The desired target distribution for the classes in the selected subset of samples.
                The length of the target must match the number of classes in the class
                distributions.
            strength:
                The strength of the balancing strategy.
        """
        # Convert to ndarray with float32 dtype if not already
        if isinstance(class_distributions, np.ndarray) and class_distributions.dtype == np.float32:
            class_distributions_nparray = class_distributions
        else:
            class_distributions_nparray = np.array(class_distributions, dtype=np.float32)
        self._check_consistent_input_size(class_distributions_nparray.shape[0])
        target_nparray = np.array(target, dtype=np.float32)
        if class_distributions_nparray.shape[1] != target_nparray.shape[0]:
            raise ValueError(
                f"The length of 'target' {target_nparray.shape[0]} doesn't match the width of "
                f"'class_distributions': {class_distributions_nparray.shape[0]}"
            )
        self.mundig.add_balancing_strategy(
            class_distributions=class_distributions_nparray,
            target=target_nparray,
            strength=strength,
        )

    def _check_consistent_input_size(self, n_input_samples_strategy: int) -> None:
        """Assert that input samples count is consistent across strategies.

        Args:
            n_input_samples_strategy:
                The number of input samples in the currently added strategy.

        Raises:
            ValueError:
                If the number of input samples in the new strategy differs
                from the one used in previous strategies.
        """
        if self.n_input_samples is None:
            self.n_input_samples = n_input_samples_strategy
        elif self.n_input_samples != n_input_samples_strategy:
            raise ValueError(
                f"Expected {self.n_input_samples} input samples, "
                f"but the latest strategy passed {n_input_samples_strategy}."
            )
