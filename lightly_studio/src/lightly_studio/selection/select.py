"""Provides the user python interface to selection bound to sample ids."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final
from uuid import UUID

from sqlmodel import Session

from lightly_studio.selection.select_via_db import select_via_database
from lightly_studio.selection.selection_config import (
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SelectionConfig,
    SelectionStrategy,
)


class Selection:
    """Selection interface for candidate sample ids."""

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
            dataset_id=self._dataset_id,
            n_samples_to_select=n_samples_to_select,
            selection_result_tag_name=selection_result_tag_name,
            strategies=selection_strategies,
        )
        select_via_database(
            session=self._session,
            config=config,
            input_sample_ids=self._input_sample_ids,
        )
