"""The API route that lists the actions the current user may do."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from lightly_studio.api.dependencies.authorization import Action, PolicyDep
from lightly_studio.api.dependencies.identity import IdentityDep

capabilities_router = APIRouter()


class CapabilitiesView(BaseModel):
    """The actions the current user may do."""

    actions: list[Action]


@capabilities_router.get("/capabilities")
def get_capabilities(identity: IdentityDep, policy: PolicyDep) -> CapabilitiesView:
    """Get the actions the current user may do."""
    return CapabilitiesView(
        actions=[a for a in Action if policy.allows(identity=identity, action=a)]
    )
