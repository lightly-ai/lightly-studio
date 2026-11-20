from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from lightly_studio.transport.annotation_transport import AnnotationTransport
from lightly_studio.transport.remote.http_annotation_transport import HttpAnnotationTransport


class TestHttpAnnotationTransport:
    def test_get_or_create_labels(self) -> None:
        transport: AnnotationTransport = HttpAnnotationTransport(client=httpx.Client())

        with pytest.raises(NotImplementedError):
            transport.get_or_create_labels(dataset_id=uuid4(), label_names=["cat"])

    def test_get_by_sample_ids(self) -> None:
        transport: AnnotationTransport = HttpAnnotationTransport(client=httpx.Client())

        with pytest.raises(NotImplementedError):
            transport.get_by_sample_ids(sample_ids=[uuid4()])

    def test_create(self) -> None:
        transport: AnnotationTransport = HttpAnnotationTransport(client=httpx.Client())

        with pytest.raises(NotImplementedError):
            transport.create(
                parent_collection_id=uuid4(),
                annotations=[],
                collection_name=None,
                covered_sample_ids=[],
            )

    def test_delete(self) -> None:
        transport: AnnotationTransport = HttpAnnotationTransport(client=httpx.Client())

        with pytest.raises(NotImplementedError):
            transport.delete(annotation_ids=[uuid4()])

    def test_get_free_object_track_numbers(self) -> None:
        transport: AnnotationTransport = HttpAnnotationTransport(client=httpx.Client())

        with pytest.raises(NotImplementedError):
            transport.get_free_object_track_numbers(dataset_id=uuid4(), count=1)

    def test_create_object_tracks(self) -> None:
        transport: AnnotationTransport = HttpAnnotationTransport(client=httpx.Client())

        with pytest.raises(NotImplementedError):
            transport.create_object_tracks(tracks=[])
