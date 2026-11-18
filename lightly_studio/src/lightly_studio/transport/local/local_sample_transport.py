"""Sample transport that calls the services in the same process."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.errors import NotFoundError, QueryExprError
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleView
from lightly_studio.models.sample_query import SamplePage, SampleQueryRequest
from lightly_studio.resolvers import collection_resolver, sample_resolver
from lightly_studio.services.sample_services import sample_query_service


class LocalSampleTransport:
    """Implements `SampleTransport` with the persistent database session."""

    def get_by_ids(self, sample_ids: Sequence[UUID]) -> list[SampleView]:
        """Get samples by ID. Samples that do not exist are not in the result."""
        samples = sample_resolver.get_many_by_id(
            session=db_manager.persistent_session(), sample_ids=list(sample_ids)
        )
        return [SampleView.model_validate(sample) for sample in samples]

    def query(self, collection_id: UUID, request: SampleQueryRequest) -> SamplePage:
        """Get one page of the image samples of a collection that match a request.

        Raises:
            NotFoundError: If the collection does not exist.
        """
        session = db_manager.persistent_session()
        collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        if collection is None:
            raise NotFoundError(f"Collection with ID {collection_id} not found.")
        if collection.sample_type != SampleType.IMAGE:
            raise ValueError("The sample query supports only image collections.")
        try:
            return sample_query_service.query_samples(
                session=session, collection_id=collection_id, request=request
            )
        except QueryExprError as error:
            # Same error as HttpTransport, which gets status 400 for it
            raise ValueError(str(error)) from error
