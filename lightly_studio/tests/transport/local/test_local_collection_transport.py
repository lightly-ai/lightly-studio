from __future__ import annotations

import uuid

import pytest

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.transport.collection_transport import CollectionTransport
from lightly_studio.transport.local.local_collection_transport import LocalCollectionTransport


@pytest.mark.usefixtures("patch_collection")
class TestLocalCollectionTransport:
    def test_create(self) -> None:
        transport: CollectionTransport = LocalCollectionTransport()

        root = transport.create(
            collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE)
        )
        child = transport.create(
            collection=CollectionCreate(
                name="child",
                sample_type=SampleType.ANNOTATION,
                parent_collection_id=root.collection_id,
            )
        )

        assert root.name == "root"
        assert root.parent_collection_id is None
        assert child.parent_collection_id == root.collection_id
        assert child.dataset_id == root.dataset_id

    def test_create__duplicate_name(self) -> None:
        transport: CollectionTransport = LocalCollectionTransport()
        collection = CollectionCreate(name="root", sample_type=SampleType.IMAGE)
        transport.create(collection=collection)

        with pytest.raises(ValueError, match=r"A dataset named 'root' already exists"):
            transport.create(collection=collection)

    def test_get_by_id(self) -> None:
        transport: CollectionTransport = LocalCollectionTransport()
        created = transport.create(
            collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE)
        )

        assert transport.get_by_id(collection_id=created.collection_id) == created
        assert transport.get_by_id(collection_id=uuid.uuid4()) is None

    def test_get_by_id__no_children(self) -> None:
        transport: CollectionTransport = LocalCollectionTransport()
        root = transport.create(
            collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE)
        )
        transport.create(
            collection=CollectionCreate(
                name="child",
                sample_type=SampleType.ANNOTATION,
                parent_collection_id=root.collection_id,
            )
        )

        fetched = transport.get_by_id(collection_id=root.collection_id)

        assert fetched is not None
        assert fetched.children == []

    def test_get_by_name(self) -> None:
        transport: CollectionTransport = LocalCollectionTransport()
        created = transport.create(
            collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE)
        )

        assert transport.get_by_name(name="root", parent_collection_id=None) == created
        assert transport.get_by_name(name="other", parent_collection_id=None) is None

    def test_get_or_create_child(self) -> None:
        transport: CollectionTransport = LocalCollectionTransport()
        root = transport.create(
            collection=CollectionCreate(name="root", sample_type=SampleType.IMAGE)
        )

        child_id = transport.get_or_create_child(
            collection_id=root.collection_id, sample_type=SampleType.ANNOTATION, name="labels"
        )
        same_child_id = transport.get_or_create_child(
            collection_id=root.collection_id, sample_type=SampleType.ANNOTATION, name="labels"
        )

        assert same_child_id == child_id
        child = transport.get_by_id(collection_id=child_id)
        assert child is not None
        assert child.name == "labels"
        assert child.parent_collection_id == root.collection_id
