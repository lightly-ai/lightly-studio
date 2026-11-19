"""Sample transport that calls the services in the same process."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.sample import SampleView
from lightly_studio.models.sample_query import SamplePage, SampleQueryRequest
from lightly_studio.resolvers import sample_resolver
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
        """Get one page of the image samples of a collection that match a request."""
        return sample_query_service.query_samples(
            session=db_manager.persistent_session(), collection_id=collection_id, request=request
        )
