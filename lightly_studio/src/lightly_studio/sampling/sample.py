"""Provides the user python interface to sampling bound to sample ids."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final, Literal
from uuid import UUID

from sqlmodel import Session

from lightly_studio.sampling.sampling_config import (
    AnnotationClassBalancingStrategy,
    AnnotationClassToTarget,
    EmbeddingDeduplicationStrategy,
    EmbeddingDiversityStrategy,
    MetadataBalancingStrategy,
    MetadataValueToTarget,
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
    # Select 100 samples balanced over the values of the "weather" metadata
    sampling.metadata_balancing(
        n_samples_to_select=100,
        sampling_result_tag_name="balanced weather sampling",
        metadata_key="weather",
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

    # Video sequence sampling.

    On video frame collections, `diverse()` can select whole frame sequences by setting
    `selected_sequence_length` to the number of frames per sequence; leaving it as `None`
    selects individual frames. `n_samples_to_select` still counts frames and must be a
    multiple of the sequence length. Only diversity strategies support sequences.
    ```python
    frames.query().sampling().diverse(
        n_samples_to_select=100,
        sampling_result_tag_name="sequence_clips",
        selected_sequence_length=50,
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
        preselected_tag_name: str | None = None,
    ) -> None:
        """Select a subset based on numeric metadata weights.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            metadata_key: Metadata key used as weights (float or int values).
            preselected_tag_name: Optional tag containing samples that should be treated
                as already selected. These samples are excluded from the result tag.
        """
        strategy = MetadataWeightingStrategy(metadata_key=metadata_key)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            sampling_strategies=[strategy],
            preselected_tag_name=preselected_tag_name,
        )

    def diverse(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        embedding_model_name: str | None = None,
        preselected_tag_name: str | None = None,
        selected_sequence_length: int | None = None,
    ) -> None:
        """Select a diverse subset using embeddings.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            embedding_model_name: Optional embedding model name. If None, uses the only
                available model or raises if multiple exist.
            preselected_tag_name: Optional tag containing samples that should be treated
                as already selected. These samples are excluded from the result tag.
            selected_sequence_length: Number of frames per selected sequence, at least
                2. ``None`` selects individual samples. When set, selection happens over
                video-frame sequences formed per video from the candidate frames in
                frame-number order, while ``n_samples_to_select`` still counts frames and
                must be a multiple of this value.
        """
        strategy = EmbeddingDiversityStrategy(embedding_model_name=embedding_model_name)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            sampling_strategies=[strategy],
            preselected_tag_name=preselected_tag_name,
            selected_sequence_length=selected_sequence_length,
        )

    def deduplicate(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        stopping_condition_minimum_distance: float,
        embedding_model_name: str | None = None,
        preselected_tag_name: str | None = None,
    ) -> None:
        """Select a deduplicated subset using embeddings.

        Removes near-duplicates by selecting samples that are spread out in
        embedding space and stopping once the closest remaining sample would be
        nearer than `stopping_condition_minimum_distance` to the already selected
        samples. Fewer than `n_samples_to_select` samples may be selected if the
        stopping condition is reached first.

        Args:
            n_samples_to_select: Maximum number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            stopping_condition_minimum_distance: Minimum embedding distance between
                selected samples. Selection stops once no remaining sample is at
                least this far from the already selected samples.
            embedding_model_name: Optional embedding model name. If None, uses the only
                available model or raises if multiple exist.
            preselected_tag_name: Optional tag containing samples that should be treated
                as already selected. These samples are excluded from the result tag.
        """
        strategy = EmbeddingDeduplicationStrategy(
            embedding_model_name=embedding_model_name,
            stopping_condition_minimum_distance=stopping_condition_minimum_distance,
        )
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            sampling_strategies=[strategy],
            preselected_tag_name=preselected_tag_name,
        )

    def annotation_balancing(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        target_distribution: AnnotationClassToTarget | Literal["uniform"] | Literal["input"],
        preselected_tag_name: str | None = None,
    ) -> None:
        """Select a subset using annotation class balancing.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            target_distribution: Can be 'uniform', 'input',
                or a dictionary mapping class names to target ratios.
            preselected_tag_name: Optional tag containing samples that should be treated
                as already selected. These samples are excluded from the result tag.
        """
        strategy = AnnotationClassBalancingStrategy(target_distribution=target_distribution)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            sampling_strategies=[strategy],
            preselected_tag_name=preselected_tag_name,
        )

    def metadata_balancing(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        metadata_key: str,
        target_distribution: MetadataValueToTarget | Literal["uniform"] | Literal["input"],
        preselected_tag_name: str | None = None,
    ) -> None:
        """Select a subset using categorical metadata balancing.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            metadata_key: Metadata key to balance. Must be categorical (string or
                boolean values).
            target_distribution: Can be 'uniform', 'input',
                or a dictionary mapping metadata values to target ratios.
            preselected_tag_name: Optional tag containing samples that should be treated
                as already selected. These samples are excluded from the result tag.
        """
        strategy = MetadataBalancingStrategy(
            metadata_key=metadata_key,
            target_distribution=target_distribution,
        )
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            sampling_strategies=[strategy],
            preselected_tag_name=preselected_tag_name,
        )

    def multi_strategies(
        self,
        n_samples_to_select: int,
        sampling_result_tag_name: str,
        sampling_strategies: list[SamplingStrategy],
        preselected_tag_name: str | None = None,
        selected_sequence_length: int | None = None,
    ) -> None:
        """Select a subset based on multiple strategies.

        Args:
            n_samples_to_select: Number of samples to select.
            sampling_result_tag_name: Tag name for the sampling result.
            sampling_strategies: Strategies to compose for sampling.
            preselected_tag_name: Optional tag containing samples that should be treated
                as already selected. These samples are excluded from the result tag.
            selected_sequence_length: Number of frames per selected sequence, at least
                2. ``None`` selects individual samples. When set, selection happens over
                video-frame sequences formed per video from the candidate frames in
                frame-number order and only diversity strategies are supported, while
                ``n_samples_to_select`` still counts frames and must be a multiple of
                this value.
        """
        config = SamplingConfig(
            collection_id=self._dataset_id,
            n_samples_to_select=n_samples_to_select,
            sampling_result_tag_name=sampling_result_tag_name,
            preselected_tag_name=preselected_tag_name,
            strategies=sampling_strategies,
            selected_sequence_length=selected_sequence_length,
        )
        sampling_via_database(
            session=self._session,
            config=config,
            input_sample_ids=self._input_sample_ids,
        )
