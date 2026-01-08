"""Provides the user python interface to selection bound to sample ids."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final, Literal
from uuid import UUID

from sqlmodel import Session

from lightly_studio.selection.select_via_db import select_via_database
from lightly_studio.selection.selection_config import (
    AnnotationClassBalancingStrategy,
    AnnotationClassToTarget,
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SelectionConfig,
    SelectionStrategy,
)


class Selection:
    """Smart selection interface.

    The `Selection` class allows to select a subset of samples from a given set of input
    samples. There are many different strategies to select samples, e.g. diversity based
    on embeddings or weighting based on numeric metadata. Multiple strategies can be
    combined to form more complex selection strategies.

    The result of a selection is stored as a tag on the selected samples in the database.
    The `selection_result_tag_name` must be a unique tag name that is not used yet.

    # Creation of a Selection instance.

    Creation of an instance of this is easiest via the `DatasetQuery` class. By using
    a `match()` first, the samples to select from can be filtered down.
    ```python
    from lightly_studio.core.dataset_query import ImageSampleField

    # Select from all samples in the dataset.
    selection = dataset.query().selection()

    # Select only from samples with width < 256.
    query_narrow_images = dataset.query().match(ImageSampleField.width < 256)
    selection_among_narrow_images = query_narrow_images.selection()
    ```
    See the `DatasetQuery.match()` documentation for more information on filtering.
    By creating the `Selection` instance, the query is executed. Further changes to the
    query do not affect the selection instance.

    # Performing single-strategy selections.

    Once a `Selection` instance is created, different selection strategies can be
    applied to select samples. Single-strategy selections are performed by calling
    the respective method on the `Selection` instance. All methods take the number of
    samples to select and a tag name for the selection result as mandatory arguments.
    ```python
    # Select 100 diverse samples based on embeddings
    selection.diverse(
        n_samples_to_select=100,
        selection_result_tag_name="diverse selection",
    )
    # Select 50 samples weighted by numeric metadata "difficulty"
    selection.metadata_weighting(
        n_samples_to_select=50,
        selection_result_tag_name="weighted selection",
        metadata_key="difficulty",
    )
    # Select 100 samples with balanced annotation classes (e.g. uniform distribution)
    selection.annotation_balancing(
        n_samples_to_select=100,
        selection_result_tag_name="balanced selection",
        target_distribution="uniform",
    )
    ```

    # Performing multi-strategy selections.

    More complex selection strategies can be formed by combining multiple selection
    strategies. This is done via the `multi_strategies()` method, which takes a
    list of selection strategies as an argument.
    ```python
    from lightly_studio.selection.selection_config import (
        EmbeddingDiversityStrategy,
        MetadataWeightingStrategy
    )

    # Select 75 samples that are diverse and weighted by "difficulty"
    selection.multi_strategies(
        n_samples_to_select=75,
        selection_result_tag_name="diverse and weighted selection",
        selection_strategies=[
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
        """Create the selection interface.

        Args:
            dataset_id: Dataset in which the selection is performed.
            session: Database session to resolve selection dependencies.
            input_sample_ids: Candidate sample ids considered for selection.
                The iterable is consumed immediately to capture a stable snapshot.
        """
        self._dataset_id: Final[UUID] = dataset_id
        self._session: Final[Session] = session
        self._input_sample_ids: list[UUID] = list(input_sample_ids)

    def metadata_weighting(
        self,
        n_samples_to_select: int,
        selection_result_tag_name: str,
        metadata_key: str,
    ) -> None:
        """Select a subset based on numeric metadata weights.

        Args:
            n_samples_to_select: Number of samples to select.
            selection_result_tag_name: Tag name for the selection result.
            metadata_key: Metadata key used as weights (float or int values).
        """
        strategy = MetadataWeightingStrategy(metadata_key=metadata_key)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            selection_result_tag_name=selection_result_tag_name,
            selection_strategies=[strategy],
        )

    def diverse(
        self,
        n_samples_to_select: int,
        selection_result_tag_name: str,
        embedding_model_name: str | None = None,
    ) -> None:
        """Select a diverse subset using embeddings.

        Args:
            n_samples_to_select: Number of samples to select.
            selection_result_tag_name: Tag name for the selection result.
            embedding_model_name: Optional embedding model name. If None, uses the only
                available model or raises if multiple exist.
        """
        strategy = EmbeddingDiversityStrategy(embedding_model_name=embedding_model_name)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            selection_result_tag_name=selection_result_tag_name,
            selection_strategies=[strategy],
        )

    def annotation_balancing(
        self,
        n_samples_to_select: int,
        selection_result_tag_name: str,
        target_distribution: AnnotationClassToTarget | Literal["uniform"] | Literal["input"],
    ) -> None:
        """Select a subset using annotation class balancing.

        Args:
            n_samples_to_select: Number of samples to select.
            selection_result_tag_name: Tag name for the selection result.
            target_distribution: Can be 'uniform', 'input',
                or a dictionary mapping class names to target ratios.
        """
        strategy = AnnotationClassBalancingStrategy(target_distribution=target_distribution)
        self.multi_strategies(
            n_samples_to_select=n_samples_to_select,
            selection_result_tag_name=selection_result_tag_name,
            selection_strategies=[strategy],
        )

    def multi_strategies(
        self,
        n_samples_to_select: int,
        selection_result_tag_name: str,
        selection_strategies: list[SelectionStrategy],
    ) -> None:
        """Select a subset based on multiple strategies.

        Args:
            n_samples_to_select: Number of samples to select.
            selection_result_tag_name: Tag name for the selection result.
            selection_strategies: Strategies to compose for selection.
        """
        config = SelectionConfig(
            collection_id=self._dataset_id,
            n_samples_to_select=n_samples_to_select,
            selection_result_tag_name=selection_result_tag_name,
            strategies=selection_strategies,
        )
        select_via_database(
            session=self._session,
            config=config,
            input_sample_ids=self._input_sample_ids,
        )
