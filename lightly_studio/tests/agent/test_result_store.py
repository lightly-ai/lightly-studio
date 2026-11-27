from __future__ import annotations

from uuid import uuid4

import pytest

from lightly_studio.agent.result_store import ResultStore


class TestResultStore:
    def test_put(self) -> None:
        store = ResultStore()
        collection_id = uuid4()
        sample_ids = [uuid4(), uuid4()]

        first = store.put(collection_id=collection_id, sample_ids=sample_ids)
        second = store.put(collection_id=collection_id, sample_ids=[])

        assert first != second
        assert first.startswith("result_")
        assert store.get(collection_id=collection_id, handle=first) == sample_ids

    def test_put__drops_oldest(self) -> None:
        store = ResultStore(max_result_sets=2)
        collection_id = uuid4()
        first = store.put(collection_id=collection_id, sample_ids=[uuid4()])
        store.put(collection_id=collection_id, sample_ids=[uuid4()])
        store.put(collection_id=collection_id, sample_ids=[uuid4()])

        with pytest.raises(ValueError, match="Unknown result handle"):
            store.get(collection_id=collection_id, handle=first)

    def test_get__unknown_handle(self) -> None:
        store = ResultStore()
        with pytest.raises(ValueError, match="Unknown result handle 'result_7'"):
            store.get(collection_id=uuid4(), handle="result_7")

    def test_get__different_server_process(self) -> None:
        collection_id = uuid4()
        old_handle = ResultStore().put(collection_id=collection_id, sample_ids=[uuid4()])
        restarted_store = ResultStore()
        restarted_store.put(collection_id=collection_id, sample_ids=[uuid4()])

        with pytest.raises(ValueError, match="Find the samples again"):
            restarted_store.get(collection_id=collection_id, handle=old_handle)

    def test_get__other_collection(self) -> None:
        store = ResultStore()
        handle = store.put(collection_id=uuid4(), sample_ids=[uuid4()])
        with pytest.raises(ValueError, match="Unknown result handle"):
            store.get(collection_id=uuid4(), handle=handle)
