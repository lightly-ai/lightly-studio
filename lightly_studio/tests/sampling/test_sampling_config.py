"""Test the Sampling configuration models."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from lightly_studio.sampling.sampling_config import (
    EmbeddingDiversityStrategy,
    SamplingConfig,
    SamplingStrategy,
    Strategy,
)


class _StrategyWrapper(BaseModel):
    strategy: Strategy


def test_strategy__unknown_strategy_name_rejected() -> None:
    with pytest.raises(ValidationError):
        _StrategyWrapper.model_validate({"strategy": {"strategy_name": "unknown_subpart"}})


class TestSamplingConfig:
    def test_init__rejects_base_strategy(self) -> None:
        with pytest.raises(ValidationError, match="Unable to extract tag"):
            SamplingConfig(
                collection_id=uuid4(),
                n_samples_to_select=4,
                sampling_result_tag_name="selected",
                strategies=[SamplingStrategy()],  # type: ignore[list-item]
            )

    def test_model_validate_json__keeps_strategy_type(self) -> None:
        config = SamplingConfig(
            collection_id=uuid4(),
            n_samples_to_select=4,
            sampling_result_tag_name="selected",
            strategies=[EmbeddingDiversityStrategy(embedding_model_name="model")],
        )

        restored = SamplingConfig.model_validate_json(config.model_dump_json())

        assert restored.strategies == [EmbeddingDiversityStrategy(embedding_model_name="model")]

    @pytest.mark.parametrize("selected_sequence_length", [1, 0, -1])
    def test_init__rejects_sequence_length_below_two(
        self,
        selected_sequence_length: int,
    ) -> None:
        """A sequence needs at least two frames; None selects individual samples."""
        with pytest.raises(ValidationError, match="greater than or equal to 2"):
            SamplingConfig(
                collection_id=uuid4(),
                n_samples_to_select=4,
                sampling_result_tag_name="sequence_sampling",
                strategies=[EmbeddingDiversityStrategy()],
                selected_sequence_length=selected_sequence_length,
            )
