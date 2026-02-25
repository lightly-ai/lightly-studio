from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

import lightly_studio.api.routes.api.operator as operator_routes_module
import lightly_studio.plugins.operator_registry as operator_registry_module
from lightly_studio.api.routes.api.operator import (
    OperatorContextRequest,
    _build_filter_from_context,
)
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.operator_registry import OperatorRegistry
from lightly_studio.plugins.parameter import BaseParameter, BoolParameter, StringParameter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import create_collection


@pytest.fixture
def isolated_operator_registry() -> Generator[OperatorRegistry, None, None]:
    original_registry = operator_registry_module.operator_registry
    registry = OperatorRegistry()
    operator_registry_module.operator_registry = registry
    operator_routes_module.operator_registry = registry  # type: ignore [attr-defined]
    try:
        yield registry
    finally:
        operator_registry_module.operator_registry = original_registry
        operator_routes_module.operator_registry = original_registry  # type: ignore [attr-defined]


def test_get_operators__empty(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    _ = isolated_operator_registry  # ensure fixture is used for mypy
    response = test_client.get("/api/operators")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []


def test_get_operators__multiple(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    isolated_operator_registry.register(TestOperator(name="Op A"))
    isolated_operator_registry.register(TestOperator(name="Op B"))

    response = test_client.get("/api/operators")

    assert response.status_code == HTTP_STATUS_OK
    payload = response.json()
    assert {payload[0]["name"], payload[1]["name"]} == {"Op A", "Op B"}
    assert len(payload) == 2


def test_get_operator_parameters__operator_not_found(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    _ = isolated_operator_registry  # ensure fixture is used for mypy
    response = test_client.get("/api/operators/unknown-id/parameters")

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert response.json() == {"detail": "Operator 'unknown-id' not found"}


def test_get_operator_parameters__no_parameters(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    # Add an operator with empty parameters:
    isolated_operator_registry.register(EmptyParamsOperator(name="empty"))

    operator_id = _get_operator_id_by_name(isolated_operator_registry, "empty")

    response = test_client.get(f"/api/operators/{operator_id}/parameters")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == []


def test_get_operator_parameters__multiple_parameters(
    test_client: TestClient,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    # Add an operator with multiple parameters:
    # - BoolParameter(name="test flag", required=True)
    # - StringParameter(name="test str", required=True)
    isolated_operator_registry.register(TestOperator(name="multi"))

    operator_id = _get_operator_id_by_name(isolated_operator_registry, "multi")

    response = test_client.get(f"/api/operators/{operator_id}/parameters")

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == [
        {
            "name": "test flag",
            "description": "",
            "default": None,
            "required": True,
            "param_type": "bool",
        },
        {
            "name": "test str",
            "description": "",
            "default": None,
            "required": True,
            "param_type": "str",
        },
    ]


def test_execute_operator__operator_not_found(
    test_client: TestClient,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    _ = isolated_operator_registry  # ensure fixture is used for mypy
    unknown_operator_id = "missing"

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{unknown_operator_id}/execute",
        json={"parameters": {"x": 1}},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
    assert response.json() == {"detail": "Operator 'missing' not found"}


def test_execute_operator__successful(
    test_client: TestClient,
    db_session: Session,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    operator = TestOperator(name="success")
    isolated_operator_registry.register(operator)
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "success")

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={"parameters": {"test flag": True, "test str": "Some text"}},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "success": True,
        "message": "Some text " + str(db_session) + " " + str(collection_id),
    }


def _get_operator_id_by_name(registry: OperatorRegistry, target_name: str) -> str:
    for metadata in registry.get_all_metadata():
        if metadata.name == target_name:
            return metadata.operator_id
    raise AssertionError(f"Operator named '{target_name}' not found in registry metadata.")


@dataclass
class TestOperator(BaseOperator):
    name: str = "test operator"
    description: str = "used to test the operator and registry system"

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return [
            BoolParameter(name="test flag", required=True),
            StringParameter(name="test str", required=True),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.ROOT]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Execute the operator with the given parameters.

        Args:
            session: Database session.
            context: Execution context containing collection_id and optional filter.
            parameters: Parameters passed to the operator.

        Returns:
            Dictionary with 'success' (bool) and 'message' (str) keys.
        """
        return OperatorResult(
            success=bool(parameters.get("test flag")),
            message=str(parameters.get("test str"))
            + " "
            + str(session)
            + " "
            + str(context.collection_id),
        )


class EmptyParamsOperator(TestOperator):
    @property
    def parameters(self) -> list[BaseParameter]:
        return []


@dataclass
class ContextCapturingOperator(BaseOperator):
    """Encodes collection_id and filter type into the result message for assertions."""

    name: str = "context-capturing"
    description: str = "captures context for testing"

    @property
    def parameters(self) -> list[BaseParameter]:
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        return [
            OperatorScope.ROOT,
            OperatorScope.IMAGE,
            OperatorScope.VIDEO,
            OperatorScope.VIDEO_FRAME,
        ]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        filter_type = type(context.filter).__name__ if context.filter else "None"
        return OperatorResult(success=True, message=f"{context.collection_id}:{filter_type}")


@dataclass
class ImageScopeOperator(BaseOperator):
    """Operator that only supports IMAGE scope — used to test scope mismatch."""

    name: str = "image-only"
    description: str = "supports only image scope"

    @property
    def parameters(self) -> list[BaseParameter]:
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        return [OperatorScope.IMAGE]

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        _, _, _ = session, context, parameters
        return OperatorResult(success=True, message="ok")


# ---------------------------------------------------------------------------
# Unit tests: _build_filter_from_context
# ---------------------------------------------------------------------------


def test_build_filter_from_context__no_sample_id__returns_passthrough() -> None:
    image_filter = ImageFilter()
    ctx = OperatorContextRequest(filter=image_filter)
    result = _build_filter_from_context(context=ctx, sample_type=SampleType.IMAGE)
    assert result is image_filter


def test_build_filter_from_context__sample_id_image_collection() -> None:
    sample_id = uuid4()
    ctx = OperatorContextRequest(sample_id=sample_id)
    result = _build_filter_from_context(context=ctx, sample_type=SampleType.IMAGE)
    assert isinstance(result, ImageFilter)
    assert result.sample_filter == SampleFilter(sample_ids=[sample_id])


def test_build_filter_from_context__sample_id_video_collection() -> None:
    sample_id = uuid4()
    ctx = OperatorContextRequest(sample_id=sample_id)
    result = _build_filter_from_context(context=ctx, sample_type=SampleType.VIDEO)
    assert isinstance(result, VideoFilter)
    assert result.sample_filter == SampleFilter(sample_ids=[sample_id])


def test_build_filter_from_context__sample_id_video_frame_collection() -> None:
    sample_id = uuid4()
    ctx = OperatorContextRequest(sample_id=sample_id)
    result = _build_filter_from_context(context=ctx, sample_type=SampleType.VIDEO_FRAME)
    assert isinstance(result, VideoFrameFilter)
    assert result.sample_filter == SampleFilter(sample_ids=[sample_id])


# ---------------------------------------------------------------------------
# Integration tests: execute_operator with context
# ---------------------------------------------------------------------------


def test_execute_operator__context_sample_id_and_filter__returns_422(
    test_client: TestClient,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    """Providing both sample_id and filter in context is rejected at validation."""
    _ = isolated_operator_registry
    sample_id = uuid4()
    response = test_client.post(
        f"/api/operators/collections/{collection_id}/any-op/execute",
        json={
            "parameters": {},
            "context": {"sample_id": str(sample_id), "filter": {}},
        },
    )
    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_execute_operator__no_context__uses_route_collection(
    test_client: TestClient,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    """When no context is given the operator is invoked directly with the route collection_id."""
    isolated_operator_registry.register(ContextCapturingOperator())
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "context-capturing")

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={"parameters": {}},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"success": True, "message": f"{collection_id}:None"}


def test_execute_operator__context_collection_id_overrides_route(
    test_client: TestClient,
    db_session: Session,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    """context.collection_id takes precedence over the route collection_id."""
    isolated_operator_registry.register(ContextCapturingOperator())
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "context-capturing")
    sub_collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={"parameters": {}, "context": {"collection_id": str(sub_collection.collection_id)}},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["message"].startswith(str(sub_collection.collection_id))


def test_execute_operator__context_collection_not_found__returns_404(
    test_client: TestClient,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    isolated_operator_registry.register(ContextCapturingOperator())
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "context-capturing")

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={"parameters": {}, "context": {"collection_id": str(uuid4())}},
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_execute_operator__scope_mismatch__returns_422(
    test_client: TestClient,
    db_session: Session,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    """An operator that doesn't support the collection's scope returns 422."""
    isolated_operator_registry.register(ImageScopeOperator())
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "image-only")
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={"parameters": {}, "context": {"collection_id": str(video_collection.collection_id)}},
    )

    assert response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY


def test_execute_operator__context_filter_passed_through(
    test_client: TestClient,
    db_session: Session,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    """When sample_id is absent, context.filter is forwarded unchanged to the operator."""
    isolated_operator_registry.register(ContextCapturingOperator())
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "context-capturing")
    image_collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={
            "parameters": {},
            "context": {"collection_id": str(image_collection.collection_id), "filter": {}},
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["message"].endswith(":ImageFilter")


def test_execute_operator__sample_id_builds_image_filter(
    test_client: TestClient,
    db_session: Session,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    isolated_operator_registry.register(ContextCapturingOperator())
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "context-capturing")
    image_collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={
            "parameters": {},
            "context": {
                "collection_id": str(image_collection.collection_id),
                "sample_id": str(uuid4()),
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["message"].endswith(":ImageFilter")


def test_execute_operator__sample_id_builds_video_filter(
    test_client: TestClient,
    db_session: Session,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    isolated_operator_registry.register(ContextCapturingOperator())
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "context-capturing")
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={
            "parameters": {},
            "context": {
                "collection_id": str(video_collection.collection_id),
                "sample_id": str(uuid4()),
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["message"].endswith(":VideoFilter")


def test_execute_operator__sample_id_builds_video_frame_filter(
    test_client: TestClient,
    db_session: Session,
    collection_id: UUID,
    isolated_operator_registry: OperatorRegistry,
) -> None:
    isolated_operator_registry.register(ContextCapturingOperator())
    operator_id = _get_operator_id_by_name(isolated_operator_registry, "context-capturing")
    video_frame_collection = create_collection(
        session=db_session, sample_type=SampleType.VIDEO_FRAME
    )

    response = test_client.post(
        f"/api/operators/collections/{collection_id}/{operator_id}/execute",
        json={
            "parameters": {},
            "context": {
                "collection_id": str(video_frame_collection.collection_id),
                "sample_id": str(uuid4()),
            },
        },
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json()["message"].endswith(":VideoFrameFilter")
