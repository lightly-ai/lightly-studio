from __future__ import annotations

import dataclasses
import sys
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, APIWebSocketRoute

from lightly_studio.api import app as app_module
from lightly_studio.api.dependencies import authorization, identity
from lightly_studio.api.dependencies.authorization import Action
from lightly_studio.api.dependencies.identity import Identity, Role
from lightly_studio.api.replaceable import NOT_REPLACEABLE, Replaceable

_DEPENDENCIES_PACKAGE = "lightly_studio.api.dependencies."


class TestReplaceable:
    def test_init(self) -> None:
        replace = Replaceable()

        assert replace.get_identity is identity.get_identity
        assert replace.get_policy is authorization.get_policy

    def test_init__replacement(self) -> None:
        replace = Replaceable(get_identity=identity.get_proxy_identity)

        assert replace.get_identity is identity.get_proxy_identity
        assert replace.get_policy is authorization.get_policy

    def test_fields(self) -> None:
        defaults = {field.name: field.default for field in dataclasses.fields(Replaceable)}

        assert defaults == {
            "get_identity": identity.get_identity,
            "get_policy": authorization.get_policy,
        }


def test_not_replaceable() -> None:
    # Each function of the dependencies package in a route is replaceable or listed.
    app = app_module.create_app()

    assert _unlisted_dependencies(app=app) == set()


def test_not_replaceable__require_is_listed() -> None:
    router = APIRouter()

    @router.delete(
        "/thing", dependencies=[Depends(authorization.require(action=Action.DATASET_DELETE))]
    )
    def delete_thing() -> None:
        pass

    app = app_module.create_app(routers=[router])

    assert _unlisted_dependencies(app=app) == set()


def test_not_replaceable__unlisted_function() -> None:
    router = APIRouter()

    @router.get("/thing")
    def get_thing(user: Annotated[Identity, Depends(identity.get_proxy_identity)]) -> None:
        pass

    app = app_module.create_app(routers=[router])

    assert _unlisted_dependencies(app=app) == {
        "lightly_studio.api.dependencies.identity.get_proxy_identity"
    }


def test_not_replaceable__unlisted_factory() -> None:
    router = APIRouter()

    @router.get("/thing", dependencies=[Depends(identity.require_role(min_role=Role.EDITOR))])
    def get_thing() -> None:
        pass

    app = app_module.create_app(routers=[router])

    assert _unlisted_dependencies(app=app) == {
        "lightly_studio.api.dependencies.identity.require_role"
    }


def _unlisted_dependencies(app: FastAPI) -> set[str]:
    """Returns the dependencies package functions in `app` that are not listed.

    A function is listed if it is a field default of `Replaceable` or in `NOT_REPLACEABLE`.
    """
    defaults = Replaceable()
    listed = {getattr(defaults, field.name) for field in dataclasses.fields(Replaceable)}
    listed |= set(NOT_REPLACEABLE)
    used: set[Callable[..., Any]] = set()
    for route in app.routes:
        if isinstance(route, (APIRoute, APIWebSocketRoute)):
            used |= _package_functions(dependant=route.dependant)
    return {f"{function.__module__}.{function.__qualname__}" for function in used - listed}


def _package_functions(dependant: Dependant) -> set[Callable[..., Any]]:
    """Returns the dependencies package functions that `dependant` uses, also indirectly.

    A closure counts as the function that creates it, for example `authorization.require`.
    """
    functions: set[Callable[..., Any]] = set()
    for sub_dependant in dependant.dependencies:
        call = sub_dependant.call
        module_name = getattr(call, "__module__", "")
        if call is not None and module_name.startswith(_DEPENDENCIES_PACKAGE):
            # A closure has the qualified name "<factory>.<locals>.<name>".
            name = call.__qualname__.split(".<locals>.")[0]
            functions.add(getattr(sys.modules[module_name], name))
        functions |= _package_functions(dependant=sub_dependant)
    return functions
