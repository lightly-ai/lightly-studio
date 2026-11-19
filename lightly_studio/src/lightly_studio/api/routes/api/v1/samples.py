"""v1 route to query the samples of a collection."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from lightly_studio.api.routes.api.v1 import collections
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample_query import SamplePage, SampleQueryRequest
from lightly_studio.services.sample_services import sample_query_service

samples_router = APIRouter()


@samples_router.post("/collections/{collection_id}/samples:query", response_model=SamplePage)
def v1_query_samples(
    session: SessionDep, collection_id: UUID, request: SampleQueryRequest
) -> SamplePage:
    """Get one page of the samples of an image collection."""
    collection = collections.get_collection(session=session, collection_id=collection_id)
    if collection.sample_type != SampleType.IMAGE:
        raise ValueError("The sample query supports only image collections.")
    return sample_query_service.query_samples(
        session=session, collection_id=collection_id, request=request
    )
