"""The router of the stable v1 API. Routes stay compatible within a major version."""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.api.routes.api.v1 import collections, samples, tags

v1_router = APIRouter(prefix="/v1", tags=["v1"])
v1_router.include_router(collections.collections_router)
v1_router.include_router(samples.samples_router)
v1_router.include_router(tags.tags_router)
