from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from lightly_studio.transport.annotation_transport import AnnotationTransport
from lightly_studio.transport.remote.http_annotation_transport import HttpAnnotationTransport


class TestHttpAnnotationTransport:
    def test_get_or_create_labels(self) -> None:
        with httpx.Client() as client, pytest.raises(NotImplementedError):
            transport: AnnotationTransport = HttpAnnotationTransport(client=client)
            transport.get_or_create_labels(dataset_id=uuid4(), label_names=["cat"])

    def test_get_by_sample_ids(self) -> None:
        with httpx.Client() as client, pytest.raises(NotImplementedError):
            transport: AnnotationTransport = HttpAnnotationTransport(client=client)
            transport.get_by_sample_ids(sample_ids=[uuid4()])

    def test_create(self) -> None:
        with httpx.Client() as client, pytest.raises(NotImplementedError):
            transport: AnnotationTransport = HttpAnnotationTransport(client=client)
            transport.create(parent_collection_id=uuid4(), annotations=[], collection_name=None)

    def test_delete(self) -> None:
        with httpx.Client() as client, pytest.raises(NotImplementedError):
            transport: AnnotationTransport = HttpAnnotationTransport(client=client)
            transport.delete(annotation_ids=[uuid4()])
