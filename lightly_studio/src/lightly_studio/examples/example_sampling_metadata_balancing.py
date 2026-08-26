"""Example of how to balance a sampling over the values of a categorical metadata key.

The example dataset has no categorical metadata, so the script first assigns a skewed
`weather` value to every sample. It then selects a subset that holds an equal share of
every value and prints both distributions to show the effect.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any
from uuid import UUID

from environs import Env

import lightly_studio as ls
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.database import db_manager

METADATA_KEY = "weather"
N_SAMPLES_TO_SELECT = 30

# Skewed input distribution: out of every ten samples, seven are sunny, two rainy and one foggy.
WEATHER_CYCLE = ["sunny"] * 7 + ["rainy"] * 2 + ["foggy"]


def main() -> None:
    """Balance a sampling over a categorical metadata key and print the distributions."""
    env = Env()
    env.read_env()
    dataset_path = env.path("EXAMPLES_DATASET_PATH")

    # Cleanup an existing database.
    db_manager.connect(cleanup_existing=True)

    # Create a Dataset from a path.
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=str(dataset_path))

    # Give every sample a weather value.
    sample_ids = [sample.sample_id for sample in dataset.query().to_list()]
    weather_per_sample = _assign_weather(sample_ids=sample_ids)
    sample_metadata: list[tuple[UUID, Mapping[str, Any]]] = [
        (sample_id, {METADATA_KEY: weather}) for sample_id, weather in weather_per_sample.items()
    ]
    dataset.update_metadata(sample_metadata=sample_metadata)
    _print_distribution(name="Input", values=weather_per_sample.values())

    # Select an equal share of every weather value.
    dataset.query().sampling().metadata_balancing(
        n_samples_to_select=N_SAMPLES_TO_SELECT,
        sampling_result_tag_name="balanced_uniform",
        metadata_key=METADATA_KEY,
        target_distribution="uniform",
    )
    _print_distribution(
        name="Uniform",
        values=_get_weather_of_tag(dataset=dataset, tag_name="balanced_uniform"),
    )

    # Select an explicit share per weather value instead. Values without a target, here
    # "foggy", share the remainder of 1.0.
    dataset.query().sampling().metadata_balancing(
        n_samples_to_select=N_SAMPLES_TO_SELECT,
        sampling_result_tag_name="balanced_custom",
        metadata_key=METADATA_KEY,
        target_distribution={"sunny": 0.5, "rainy": 0.3},
    )
    _print_distribution(
        name="Custom",
        values=_get_weather_of_tag(dataset=dataset, tag_name="balanced_custom"),
    )

    ls.start_gui()


def _assign_weather(sample_ids: Sequence[UUID]) -> dict[UUID, str]:
    """Assign a weather value to every sample by cycling through `WEATHER_CYCLE`.

    Args:
        sample_ids: The samples to assign a value to.

    Returns:
        The weather value per sample id.
    """
    return {
        sample_id: WEATHER_CYCLE[index % len(WEATHER_CYCLE)]
        for index, sample_id in enumerate(sample_ids)
    }


def _get_weather_of_tag(dataset: ls.ImageDataset, tag_name: str) -> list[str]:
    """Read the weather value of every sample that carries the given tag."""
    samples = dataset.query().match(ImageSampleField.tags.contains(tag_name)).to_list()
    return [sample.metadata[METADATA_KEY] for sample in samples]


def _print_distribution(name: str, values: Iterable[str]) -> None:
    """Print the number of samples per weather value."""
    counts = Counter(values)
    per_value = "  ".join(f"{value}={count}" for value, count in sorted(counts.items()))
    print(f"{name} distribution ({sum(counts.values())} samples): {per_value}")


if __name__ == "__main__":
    main()
