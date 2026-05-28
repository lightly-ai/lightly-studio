"""Provides the user python interface to sampling bound to sample ids."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final, Literal
from uuid import UUID

from sqlmodel import Session

from lightly_studio.sampling.sampling_config import (
    AnnotationClassBalancingStrategy,
    AnnotationClassToTarget,
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SamplingConfig,
    SamplingStrategy,
)
from lightly_studio.sampling.sampling_via_db import sampling_via_database


class Sampling:
    """Smart sampling interface.

    The `Sampling` class allows to select a subset of samples from a given set of input
    samples. There are many different strategies to select samples, e.g. diversity based
    on embeddings or weighting based on numeric metadata. Multiple strategies can be
    combined to form more complex sampling strategies.

    The result of a sampling is stored as a tag on the selected samples in the database.
    The `sampling_result_tag_name` must be a unique tag name that is not used yet.

    # Creation of a Sampling instance.

    Creation of an instance of this is easiest via the `DatasetQuery` class. By using
    a `match()` first, the samples to select from can be filtered down.
    ```python
    from lightly_studio.core.dataset_query import ImageSampleField

    # Select from all samples in the dataset.
    sampling = dataset.query().sampling()

    # Select only from samples with width < 256.
    query_narrow_images = dataset.query().match(ImageSampleField.width < 256)
    sampling_among_narrow_images = query_narrow_images.sampling()
    ```
    See the `DatasetQuery.match()` documentation for more information on filtering.
    By creating the `Sampling` instance, the query is executed. Further changes to the
    query do not affect the sampling instance.

    # Performing single-strategy samplings.

    Once a `Sampling` instance is created, different sampling strategies can be
    applied to select samples. Single-strategy samplings are performed by calling
    the respective method on the `Sampling` instance. All methods take the number of
    samples to select and a tag name for the sampling result as mandatory arguments.
    ```python
    # Select 100 diverse samples based on embeddings
    sampling.diverse(
        n_samples_to_select=100,
        sampling_result_tag_name="diverse sampling",
    )
    # Select 50 samples weighted by numeric metadata "difficulty"
    sampling.metadata_weighting(
        n_samples_to_select=50,
        sampling_result_tag_name="weighted sampling",
        metadata_key="difficulty",
    )
    # Select 100 samples with balanced annotation classes (e.g. uniform distribution)
    sampling.annotation_balancing(
        n_samples_to_select=100,
        sampling_result_tag_name="balanced sampling",
        target_distribution="uniform",
    )
    ```

    # Performing multi-strategy samplings.

    More complex sampling strategies can be formed by combining multiple sampling
    strategies. This is done via the `multi_strategies()` method, which takes a
    list of sampling strategies as an argument.
    ```python
    from lightly_studio.sampling.sampling_config import (
        EmbeddingDiversityStrategy,
        MetadataWeightingStrategy
    )

    # Select 75 samples that are diverse and weighted by "difficulty"
    sampling.multi_strategies(
        n_samples_to_select=75,
        sampling_result_tag_name="diverse and weighted sampling",
        sampling_strategies=[
            EmbeddingDiversityStrategy(),
            MetadataWeightingStrategy(metadata_key="difficulty"),
        ],
    )
    ```
    """

    def __init__(
        self,
        dataset_id: UUID,
        session: Session,
        input_sample_ids: Iterable[UUID],
    ) -> None:
        """Create the sampling interface.

        Args:
            dataset_id: Dataset in which the sampling is performed.
            session: Database session to resolve sampling dependencies.
            input_sample_ids: Candidate sample ids considered for sampling.
                The iterable is consumed immediately to capture a stable snapshot.
        """
        self._dataset_id: Final[UUID] = dataset_id
        self._session: Final[Session] = session
        self._input_sample_ids: list[UUID] = list(input_sample_ids)

    def metadata_weighting(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        metadata_key: str,
    ) -> None:
        """Select a subset based on numeric metadata weights.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            metadata_key: Metadata key used as weights (float or int values).
        """
        strategy = MetadataWeightingStrategy(metadata_key=metadata_key)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            sampling_strategies=[strategy],
        )

    def diverse(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        embedding_model_name: str | None = None,
    ) -> None:
        """Select a diverse subset using embeddings.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            embedding_model_name: Optional embedding model name. If None, uses the only
                available model or raises if multiple exist.
        """
        strategy = EmbeddingDiversityStrategy(embedding_model_name=embedding_model_name)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            sampling_strategies=[strategy],
        )

    def annotation_balancing(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        target_distribution: AnnotationClassToTarget | Literal["uniform"] | Literal["input"],
    ) -> None:
        """Select a subset using annotation class balancing.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            target_distribution: Can be 'uniform', 'input',
                or a dictionary mapping class names to target ratios.
        """
        strategy = AnnotationClassBalancingStrategy(target_distribution=target_distribution)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            sampling_strategies=[strategy],
        )

    def multi_strategies(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        sampling_strategies: list[SamplingStrategy],
    ) -> None:
        """Select a subset based on multiple strategies.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            sampling_strategies: Strategies to compose for sampling.
        """
        config = SamplingConfig(
            collection_id=self._dataset_id,
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            strategies=sampling_strategies,
        )
        sampling_via_database(
            session=self._session,
            config=config,
            input_sample_ids=self._input_sample_ids,
        )
