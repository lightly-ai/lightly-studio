"""Tests for resolving metadata balancing strategies into distributions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import numpy as np
import pytest
from sqlmodel import Session

from lightly_studio.resolvers import image_resolver
from lightly_studio.sampling import metadata_balancing
from lightly_studio.sampling.sampling_config import (
    MetadataBalancingStrategy,
    MetadataValueToTarget,
)
from tests.helpers_resolvers import create_image
from tests.sampling import helpers_sampling


@pytest.mark.parametrize(
    ("metadata", "metadata_key", "target_distribution", "expected_matrix", "expected_target"),
    [
        pytest.param(
            ["sunny", "sunny", "rainy"],
            "weather",
            "uniform",
            # Columns are the sorted values ["rainy", "sunny"].
            [[0.0, 1.0], [0.0, 1.0], [1.0, 0.0]],
            [0.5, 0.5],
            id="uniform",
        ),
        pytest.param(
            ["sunny", "sunny", "rainy"],
            "weather",
            "input",
            [[0.0, 1.0], [0.0, 1.0], [1.0, 0.0]],
            # The input target holds the raw counts of ["rainy", "sunny"].
            [1.0, 2.0],
            id="input",
        ),
        pytest.param(
            [True, True, False],
            "is_blurry",
            "uniform",
            # Boolean values become their lowercase names, sorted as ["false", "true"].
            [[0.0, 1.0], [0.0, 1.0], [1.0, 0.0]],
            [0.5, 0.5],
            id="boolean",
        ),
        pytest.param(
            ["sunny", "rainy", "foggy"],
            "weather",
            # The values without a target are grouped as one "other" value, so this
            # distribution becomes `sunny: 0.5, rainy+foggy: 0.5`.
            {"sunny": 0.5},
            # Columns are ["sunny", other].
            [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]],
            [0.5, 0.5],
            id="explicit_target",
        ),
        pytest.param(
            ["sunny", "rainy"],
            "weather",
            # No sample is foggy, so that column stays empty instead of catching the
            # values without a target.
            {"sunny": 0.5, "foggy": 0.5},
            # Columns are ["sunny", "foggy", other], and "rainy" falls into "other".
            [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            [0.5, 0.5, 0.0],
            id="target_value_not_present",
        ),
        pytest.param(
            [True, True, False],
            "is_blurry",
            # A boolean key is targeted with booleans or with their lowercase names.
            {True: 0.75},
            # Columns are ["true", other], and the false sample falls into "other".
            [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
            [0.75, 0.25],
            id="boolean_explicit_target",
        ),
    ],
)
def test_get_metadata_balancing_data(  # noqa: PLR0913
    db_session: Session,
    metadata: list[Any],
    metadata_key: str,
    target_distribution: MetadataValueToTarget | str,
    expected_matrix: list[list[float]],
    expected_target: list[float],
) -> None:
    """Resolves the three target distributions into one-hot value distributions."""
    collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
        session=db_session, metadata=metadata, metadata_key=metadata_key
    )

    value_distributions, target_values = metadata_balancing.get_metadata_balancing_data(
        session=db_session,
        strat=MetadataBalancingStrategy(
            metadata_key=metadata_key,
            target_distribution=target_distribution,  # type: ignore[arg-type]
        ),
        collection_id=collection_id,
        input_sample_ids=_all_sample_ids(session=db_session, collection_id=collection_id),
    )

    np.testing.assert_array_equal(value_distributions, np.array(expected_matrix, dtype=np.float32))
    assert target_values == expected_target


def test_get_metadata_balancing_data__missing_value(db_session: Session) -> None:
    """Gives a sample without a value for the key an all-zero row."""
    collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
        session=db_session, metadata=["sunny", "rainy"], metadata_key="weather"
    )
    sample_without_value = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="no_weather.jpg"
    )
    input_sample_ids = _all_sample_ids(session=db_session, collection_id=collection_id)
    row_without_value = input_sample_ids.index(sample_without_value.sample_id)

    value_distributions, _ = metadata_balancing.get_metadata_balancing_data(
        session=db_session,
        strat=MetadataBalancingStrategy(metadata_key="weather", target_distribution="uniform"),
        collection_id=collection_id,
        input_sample_ids=input_sample_ids,
    )

    assert value_distributions.shape == (3, 2)
    np.testing.assert_array_equal(
        value_distributions[row_without_value], np.array([0.0, 0.0], dtype=np.float32)
    )


def test_get_metadata_balancing_data__no_values(db_session: Session) -> None:
    """Balances nothing when no input sample has a value for the key."""
    collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
        session=db_session, metadata=["sunny", "rainy"], metadata_key="weather"
    )
    # Restrict the input to a sample that has no value for the balanced key.
    sample_without_value = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="no_weather.jpg"
    )

    value_distributions, target_values = metadata_balancing.get_metadata_balancing_data(
        session=db_session,
        strat=MetadataBalancingStrategy(metadata_key="weather", target_distribution="uniform"),
        collection_id=collection_id,
        input_sample_ids=[sample_without_value.sample_id],
    )

    assert value_distributions.shape == (1, 0)
    assert target_values == []


def test_get_metadata_balancing_data__more_values_than_balanced(db_session: Session) -> None:
    """Groups the rarest values when the key has more distinct values than balanced."""
    n_values = metadata_balancing.MAX_BALANCED_VALUES + 5
    collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
        session=db_session,
        metadata=[f"value_{index:03d}" for index in range(n_values)],
        metadata_key="serial",
    )

    value_distributions, target_values = metadata_balancing.get_metadata_balancing_data(
        session=db_session,
        strat=MetadataBalancingStrategy(metadata_key="serial", target_distribution="uniform"),
        collection_id=collection_id,
        input_sample_ids=_all_sample_ids(session=db_session, collection_id=collection_id),
    )

    # The rarest values share one "other" column on top of the balanced ones.
    assert value_distributions.shape == (n_values, metadata_balancing.MAX_BALANCED_VALUES + 1)
    assert len(target_values) == metadata_balancing.MAX_BALANCED_VALUES + 1
    # Every sample still has exactly one value, so every row is one-hot.
    np.testing.assert_array_equal(
        value_distributions.sum(axis=1), np.ones(n_values, dtype=np.float32)
    )


def test_get_metadata_balancing_data__target_values_at_limit(db_session: Session) -> None:
    """Accepts an explicit target that holds exactly as many values as are balanced."""
    collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
        session=db_session, metadata=["sunny", "rainy"], metadata_key="weather"
    )
    target_distribution: MetadataValueToTarget = {
        f"value_{index:03d}": 0.0 for index in range(metadata_balancing.MAX_BALANCED_VALUES)
    }

    value_distributions, target_values = metadata_balancing.get_metadata_balancing_data(
        session=db_session,
        strat=MetadataBalancingStrategy(
            metadata_key="weather", target_distribution=target_distribution
        ),
        collection_id=collection_id,
        input_sample_ids=_all_sample_ids(session=db_session, collection_id=collection_id),
    )

    # No sample matches a target value, so both fall into the appended "other" column.
    assert value_distributions.shape == (2, metadata_balancing.MAX_BALANCED_VALUES + 1)
    assert len(target_values) == metadata_balancing.MAX_BALANCED_VALUES + 1


def test_get_metadata_balancing_data__too_many_target_values(db_session: Session) -> None:
    """Rejects an explicit target that holds more values than are balanced."""
    collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
        session=db_session, metadata=["sunny", "rainy"], metadata_key="weather"
    )
    target_distribution: MetadataValueToTarget = {
        f"value_{index:03d}": 0.0 for index in range(metadata_balancing.MAX_BALANCED_VALUES + 1)
    }

    with pytest.raises(ValueError, match="supports at most"):
        metadata_balancing.get_metadata_balancing_data(
            session=db_session,
            strat=MetadataBalancingStrategy(
                metadata_key="weather", target_distribution=target_distribution
            ),
            collection_id=collection_id,
            input_sample_ids=_all_sample_ids(session=db_session, collection_id=collection_id),
        )


def test_get_metadata_balancing_data__duplicate_target_value(db_session: Session) -> None:
    """Rejects an explicit target that names the same boolean value twice."""
    collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
        session=db_session, metadata=[True, False], metadata_key="is_blurry"
    )

    with pytest.raises(ValueError, match="two targets for the value 'true'"):
        metadata_balancing.get_metadata_balancing_data(
            session=db_session,
            strat=MetadataBalancingStrategy(
                metadata_key="is_blurry", target_distribution={True: 0.5, "true": 0.5}
            ),
            collection_id=collection_id,
            input_sample_ids=_all_sample_ids(session=db_session, collection_id=collection_id),
        )


@pytest.mark.parametrize(
    ("metadata", "metadata_key", "balanced_key", "expected_error"),
    [
        pytest.param(
            [0.1, 0.2, 0.3],
            "sharpness",
            "sharpness",
            "has type 'float', but balancing requires",
            id="non_categorical_key",
        ),
        pytest.param(
            ["sunny", "rainy"],
            "weather",
            "missing",
            "does not exist in collection",
            id="unknown_key",
        ),
    ],
)
def test_get_metadata_balancing_data__invalid_key(
    db_session: Session,
    metadata: list[Any],
    metadata_key: str,
    balanced_key: str,
    expected_error: str,
) -> None:
    """Rejects a key that does not exist in the collection or is not categorical."""
    collection_id = helpers_sampling.fill_db_with_samples_and_metadata(
        session=db_session, metadata=metadata, metadata_key=metadata_key
    )

    with pytest.raises(ValueError, match=expected_error):
        metadata_balancing.get_metadata_balancing_data(
            session=db_session,
            strat=MetadataBalancingStrategy(
                metadata_key=balanced_key, target_distribution="uniform"
            ),
            collection_id=collection_id,
            input_sample_ids=_all_sample_ids(session=db_session, collection_id=collection_id),
        )


def _all_sample_ids(session: Session, collection_id: UUID) -> list[UUID]:
    """Return all sample ids of the collection, ordered as the resolver returns them."""
    samples = image_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id, pagination=None
    ).samples
    return [sample.sample_id for sample in samples]
