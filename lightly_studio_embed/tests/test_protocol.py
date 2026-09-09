from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from lightly_studio_embed.embedder import Capability
from lightly_studio_embed.protocol import (
    MAX_ABS_EMBEDDING_VALUE,
    WIRE_CAPABILITIES,
    DescribeResponse,
    EmbeddingsResponse,
    ServerLimits,
)

SPACE_KEY = "acme/model@v1"


def test_describe_response() -> None:
    response = _describe(capabilities=[Capability.TEXT, Capability.IMAGE_BYTES])

    assert response.protocol_version == "1.0"
    assert response.capabilities == [Capability.TEXT, Capability.IMAGE_BYTES]


def test_describe_response__every_wire_capability_is_accepted() -> None:
    response = _describe(capabilities=sorted(WIRE_CAPABILITIES))

    assert set(response.capabilities) == WIRE_CAPABILITIES


def test_describe_response__rejects_an_unservable_capability() -> None:
    """LightlyStudio cannot request this kind. A server must not advertise it."""
    with pytest.raises(ValidationError, match="cannot be served over HTTP"):
        _describe(capabilities=[Capability.TEXT, Capability.IMAGE_PIL])


def test_describe_response__rejects_a_dimension_of_zero() -> None:
    """A zero-width space puts empty vectors into a similarity search."""
    with pytest.raises(ValidationError, match="greater than 0"):
        DescribeResponse(
            space_key=SPACE_KEY,
            dimension=0,
            ready=True,
            capabilities=[Capability.TEXT],
            limits=ServerLimits(),
        )


def test_describe_response__keeps_a_numpy_integer_dimension() -> None:
    """An embedder reads its dimension from a model. A model returns an ``np.int64``."""
    response = DescribeResponse(
        space_key=SPACE_KEY,
        dimension=np.int64(512),  # type: ignore[arg-type]
        ready=True,
        capabilities=[Capability.TEXT],
        limits=ServerLimits(),
    )

    assert response.dimension == 512


def test_describe_response__keeps_an_unknown_protocol_version() -> None:
    """A client must name the version that it met. The body must still parse."""
    response = DescribeResponse.model_validate(
        {
            "protocol_version": "99.0",
            "space_key": SPACE_KEY,
            "dimension": 2,
            "ready": True,
            "capabilities": [Capability.TEXT],
            "limits": {},
        }
    )

    assert response.protocol_version == "99.0"


def test_wire_capabilities__holds_every_kind_but_the_pil_image() -> None:
    """An fsspec path crosses the wire. A PIL image is an object in this process only."""
    assert frozenset(Capability) - WIRE_CAPABILITIES == {Capability.IMAGE_PIL}


def test_embeddings_response() -> None:
    response = _embeddings(kept_indices=[0, 2], embeddings=[[0.5, -0.5], [1.0, 0.0]])

    assert response.kept_indices == [0, 2]
    assert response.embeddings == [[0.5, -0.5], [1.0, 0.0]]


def test_embeddings_response__row_count_mismatch() -> None:
    """A client reads this model from a server that it does not control. The model checks."""
    with pytest.raises(ValidationError, match="1 embeddings for 2 kept indices"):
        _embeddings(kept_indices=[0, 1], embeddings=[[0.5, -0.5]])


def test_embeddings_response__kept_indices_not_ascending() -> None:
    with pytest.raises(ValidationError, match="ascending and unique"):
        _embeddings(kept_indices=[1, 1], embeddings=[[0.5, -0.5], [1.0, 0.0]])


def test_embeddings_response__negative_kept_index() -> None:
    """A negative index selects an item from the end of the request."""
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        _embeddings(kept_indices=[-1], embeddings=[[0.5, -0.5]])


def test_embeddings_response__kept_indices_are_a_json_boolean_mask() -> None:
    """A lax int field reads ``[false, true]`` as the indices ``[0, 1]``."""
    with pytest.raises(ValidationError, match="bool, not an index"):
        EmbeddingsResponse.model_validate(
            {
                "space_key": SPACE_KEY,
                "dimension": 2,
                "kept_indices": [False, True],
                "embeddings": [[0.5, -0.5], [1.0, 0.0]],
            }
        )


def test_embeddings_response__kept_indices_are_a_numpy_boolean_mask() -> None:
    """``np.bool_`` is not a ``bool``. An embedder in this process produces one."""
    with pytest.raises(ValidationError, match="bool, not an index"):
        _embeddings(
            kept_indices=list(np.array([False, True])),
            embeddings=[[0.5, -0.5], [1.0, 0.0]],
        )


def test_embeddings_response__kept_index_not_integral() -> None:
    """The model rejects a float index. It does not truncate the index onto the wrong item."""
    with pytest.raises(ValidationError, match="valid integer"):
        _embeddings(
            kept_indices=[0.9],  # type: ignore[list-item]
            embeddings=[[0.5, -0.5]],
        )


def test_embeddings_response__wrong_dimension() -> None:
    with pytest.raises(ValidationError, match="has 3 values"):
        _embeddings(kept_indices=[0], embeddings=[[0.5, -0.5, 0.5]])


def test_embeddings_response__rejects_a_dimension_of_zero() -> None:
    """A zero-width vector clears every other check. It carries no data."""
    with pytest.raises(ValidationError, match="greater than 0"):
        _embeddings(kept_indices=[0], embeddings=[[]], dimension=0)


def test_embeddings_response__value_not_finite() -> None:
    with pytest.raises(ValidationError, match="not finite"):
        _embeddings(kept_indices=[0], embeddings=[[0.5, float("nan")]])


def test_embeddings_response__value_too_large_for_a_float32() -> None:
    """The wire carries float64. Both ends store float32, so 1e300 becomes an infinity."""
    with pytest.raises(ValidationError, match="would become an infinity"):
        _embeddings(kept_indices=[0], embeddings=[[1e300, 1.0]])


def test_embeddings_response__value_at_the_float32_limit() -> None:
    response = _embeddings(kept_indices=[0], embeddings=[[MAX_ABS_EMBEDDING_VALUE, 1.0]])

    assert response.embeddings == [[MAX_ABS_EMBEDDING_VALUE, 1.0]]


def _describe(capabilities: list[Capability]) -> DescribeResponse:
    return DescribeResponse(
        space_key=SPACE_KEY,
        dimension=2,
        ready=True,
        capabilities=capabilities,
        limits=ServerLimits(),
    )


def _embeddings(
    kept_indices: list[int], embeddings: list[list[float]], dimension: int = 2
) -> EmbeddingsResponse:
    return EmbeddingsResponse(
        space_key=SPACE_KEY,
        dimension=dimension,
        kept_indices=kept_indices,
        embeddings=embeddings,
    )
