"""Sample transport that calls the services in the same process."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from lightly_studio.database import db_manager
from lightly_studio.models.sample import SampleView
from lightly_studio.models.sample_query import SamplePage, SampleQueryRequest
from lightly_studio.resolvers import image_resolver, sample_resolver, video_resolver
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

    def get_image_ids_by_paths(
        self, collection_id: UUID, file_paths: Sequence[str]
    ) -> dict[str, UUID]:
        """Get the sample IDs of the images of a collection by absolute file path."""
        return image_resolver.get_sample_ids_by_paths(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            file_paths_abs=file_paths,
        )

    def get_video_ids_by_stems(self, collection_id: UUID) -> dict[str, UUID]:
        """Get the sample IDs of all videos of a collection by file name stem."""
        return video_resolver.get_sample_ids_by_stems(
            session=db_manager.persistent_session(), collection_id=collection_id
        )
