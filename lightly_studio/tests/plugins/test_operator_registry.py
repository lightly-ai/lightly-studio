from __future__ import annotations

import importlib.metadata
import site
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.plugins import operator_registry as _registry_module
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult, OperatorStatus
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.operator_registry import ENTRY_POINT_GROUP, OperatorRegistry
from lightly_studio.plugins.parameter import BaseParameter, BoolParameter, StringParameter
from tests.helpers_resolvers import create_collection


def test_operator_registry__empty() -> None:
    # Check if operator is already registered
    operator_registry = OperatorRegistry()
    assert operator_registry.get_by_id("some_id") is None


def test_operator_registry__dummy_operators(db_session: Session) -> None:
    # Create a local registry and register a test operator
    operator_registry = OperatorRegistry()
    input_operator = TestOperator()
    operator_registry.register(operator=input_operator)

    # Validate that the registry returns the expected values
    operator_info_list = operator_registry.get_all_metadata()
    assert len(operator_info_list) == 1
    assert operator_info_list[0].name == "test operator"

    # Validate and Execute the test operator retrieved from the registry
    operator = operator_registry.get_by_id(operator_id=operator_info_list[0].operator_id)
    assert operator == input_operator

    collection = create_collection(session=db_session)
    context = ExecutionContext(collection_id=collection.collection_id, context_filter=None)
    result = operator.execute(
        session=db_session,
        context=context,
        parameters={"test flag": True, "test str": "test value"},
    )

    assert result.success
    assert result.message == "test value " + str(db_session) + " " + str(collection.collection_id)

    # Register another operator and make sure we have two now.
    operator_registry.register(TestOperator())
    operator_info_list = operator_registry.get_all_metadata()
    assert len(operator_info_list) == 2


def test_operator__initial_status_is_pending() -> None:
    assert TestOperator().status == OperatorStatus.PENDING


def test_operator_registry__startup_all_sets_ready() -> None:
    operator = TestOperator()
    registry = OperatorRegistry()
    registry.register(operator)
    registry.startup_all()

    assert operator.status == OperatorStatus.READY


def test_operator_registry__shutdown_all_sets_stopped() -> None:
    operator = TestOperator()
    registry = OperatorRegistry()
    registry.register(operator)
    registry.startup_all()
    registry.shutdown_all()

    assert operator.status == OperatorStatus.STOPPED


def test_operator_registry__startup_all_sets_error_on_failure() -> None:
    operator = FailingStartupOperator()
    registry = OperatorRegistry()
    registry.register(operator)
    registry.startup_all()

    assert operator.status == OperatorStatus.ERROR


def test_operator_registry__startup_all_continues_after_failure() -> None:
    failing = FailingStartupOperator()
    healthy = TestOperator()
    registry = OperatorRegistry()
    registry.register(failing)
    registry.register(healthy)
    registry.startup_all()

    assert failing.status == OperatorStatus.ERROR
    assert healthy.status == OperatorStatus.READY


def test_operator_registry__discover_plugins_no_entry_points(
    mocker: MockerFixture,
) -> None:
    _patch_distributions(mocker=mocker, distributions=[])
    registry = OperatorRegistry()
    registry.discover_plugins()

    assert registry.get_all_metadata() == []


def test_operator_registry__discover_plugins_registers_valid_operator(
    mocker: MockerFixture,
) -> None:
    ep = _entry_point(mocker=mocker, name="test_plugin", loads=TestOperator)
    _patch_distributions(mocker=mocker, distributions=[_distribution(mocker, "my_package", [ep])])
    registry = OperatorRegistry()
    new_ids = registry.discover_plugins()

    metadata = registry.get_all_metadata()
    assert len(metadata) == 1
    assert metadata[0].name == "test operator"
    assert metadata[0].package_name == "my_package"
    assert new_ids == [metadata[0].operator_id]


def test_operator_registry__discover_plugins_ignores_other_groups(
    mocker: MockerFixture,
) -> None:
    ep = _entry_point(mocker=mocker, name="cli", loads=TestOperator, group="console_scripts")
    _patch_distributions(mocker=mocker, distributions=[_distribution(mocker, "my_package", [ep])])
    registry = OperatorRegistry()
    registry.discover_plugins()

    assert registry.get_all_metadata() == []


def test_operator_registry__discover_plugins_twice_no_duplicates(
    mocker: MockerFixture,
) -> None:
    ep = _entry_point(mocker=mocker, name="test_plugin", loads=TestOperator)
    _patch_distributions(mocker=mocker, distributions=[_distribution(mocker, "my_package", [ep])])
    registry = OperatorRegistry()
    registry.discover_plugins()
    new_ids = registry.discover_plugins()

    assert new_ids == []
    assert len(registry.get_all_metadata()) == 1
    ep.load.assert_called_once()


def test_operator_registry__discover_plugins_and_manual_register(
    mocker: MockerFixture,
) -> None:
    ep = _entry_point(mocker=mocker, name="test_plugin", loads=TestOperator)
    _patch_distributions(mocker=mocker, distributions=[_distribution(mocker, "my_package", [ep])])
    registry = OperatorRegistry()
    registry.discover_plugins()

    registry.register(operator=FailingStartupOperator())

    metadata = registry.get_all_metadata()
    assert len(metadata) == 2
    assert metadata[0].name == "test operator"
    assert metadata[1].name == "failing operator"
    assert metadata[1].package_name is None


def test_operator_registry__discover_plugins_skips_non_base_operator(
    mocker: MockerFixture,
) -> None:
    ep = _entry_point(mocker=mocker, name="bad_plugin", loads=lambda: "not an operator")
    _patch_distributions(mocker=mocker, distributions=[_distribution(mocker, "my_package", [ep])])
    registry = OperatorRegistry()
    registry.discover_plugins()

    assert registry.get_all_metadata() == []


def test_operator_registry__discover_plugins_skips_failing_entry_point(
    mocker: MockerFixture,
) -> None:
    ep = _entry_point(mocker=mocker, name="broken_plugin", loads=None)
    ep.load.side_effect = ImportError("module not found")
    _patch_distributions(mocker=mocker, distributions=[_distribution(mocker, "my_package", [ep])])
    registry = OperatorRegistry()
    registry.discover_plugins()

    assert registry.get_all_metadata() == []


def test_operator_registry__discover_new_plugins(
    mocker: MockerFixture,
) -> None:
    first = _entry_point(mocker=mocker, name="first", loads=TestOperator)
    second = _entry_point(mocker=mocker, name="second", loads=FailingStartupOperator)
    distributions = [_distribution(mocker, "first_package", [first])]
    _patch_distributions(mocker=mocker, distributions=distributions)
    registry = OperatorRegistry()
    registry.discover_plugins()
    registry.startup_all()

    # A second package is installed while the server runs.
    distributions.append(_distribution(mocker, "second_package", [second]))
    new_ids = registry.discover_new_plugins()

    assert len(new_ids) == 1
    new_operator = registry.get_by_id(operator_id=new_ids[0])
    assert isinstance(new_operator, FailingStartupOperator)
    assert new_operator.status == OperatorStatus.ERROR
    assert len(registry.get_all_metadata()) == 2


def test_operator_registry__discover_plugins_retries_failed_entry_point(
    mocker: MockerFixture,
) -> None:
    ep = _entry_point(mocker=mocker, name="test_plugin", loads=None)
    ep.load.side_effect = [ImportError("missing dependency"), TestOperator]
    _patch_distributions(mocker=mocker, distributions=[_distribution(mocker, "my_package", [ep])])
    registry = OperatorRegistry()

    assert registry.discover_plugins() == []
    # The missing dependency was installed before the second scan.
    assert len(registry.discover_plugins()) == 1


def test_operator_registry__discover_plugins_activates_new_pth_files(
    mocker: MockerFixture,
) -> None:
    _patch_distributions(mocker=mocker, distributions=[])
    pth_files = [Path("/site/a.pth")]
    mocker.patch.object(_registry_module, "_pth_files", side_effect=lambda: list(pth_files))
    addpackage = mocker.patch.object(site, "addpackage")
    registry = OperatorRegistry()

    # An editable install adds a .pth file while the server runs.
    pth_files.append(Path("/site/b.pth"))
    registry.discover_plugins()
    registry.discover_plugins()

    addpackage.assert_called_once_with("/site", "b.pth", None)


def _patch_distributions(mocker: MockerFixture, distributions: list[Any]) -> None:
    """Patch ``importlib.metadata.distributions`` to return *distributions*.

    The list is read on each call, so a test can append to it to simulate an install.
    """
    mocker.patch.object(
        importlib.metadata,
        "distributions",
        side_effect=lambda: list(distributions),
    )


def _distribution(mocker: MockerFixture, name: str, eps: list[Any]) -> Any:
    dist = mocker.MagicMock()
    dist.metadata = {"Name": name}
    dist.entry_points = eps
    return dist


def _entry_point(
    mocker: MockerFixture, name: str, loads: Any, group: str = ENTRY_POINT_GROUP
) -> Any:
    ep = mocker.MagicMock()
    ep.name = name
    ep.value = f"my_package:{name}"
    ep.group = group
    ep.load.return_value = loads
    return ep


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


@dataclass
class FailingStartupOperator(BaseOperator):
    name: str = "failing operator"
    description: str = "always raises during startup"

    @property
    def parameters(self) -> list[BaseParameter]:
        """Return the list of parameters this operator expects."""
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        """Return the list of scopes this operator can be triggered from."""
        return [OperatorScope.ROOT]

    def startup(self) -> None:
        """Raise to simulate a broken operator."""
        raise RuntimeError("startup failed")

    def execute(
        self,
        *,
        session: Session,
        context: ExecutionContext,
        parameters: dict[str, Any],
    ) -> OperatorResult:
        """Not expected to be called in tests."""
        raise NotImplementedError  # pragma: no cover
