"""Keeps the sample IDs that the agent tools find, behind unique handles.

A tool that finds samples does not send their IDs to the model. It stores them here and
gives the model an opaque result handle. A later tool reads the IDs back by that
handle. This keeps the prompt small and stops the model from copying UUIDs wrongly.

The store lives in the memory of the process. A restart of the server forgets every
handle, and the model then has to search again.
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from collections.abc import Sequence
from uuid import UUID

# The number of result sets that the store keeps. The oldest set is dropped first.
_MAX_RESULT_SETS = 200


class ResultStore:
    """A bounded map from a handle to an ordered list of sample IDs."""

    def __init__(self, max_result_sets: int = _MAX_RESULT_SETS) -> None:
        """Create an empty store.

        Args:
            max_result_sets: The number of result sets to keep before the oldest is dropped.
        """
        self._max_result_sets = max_result_sets
        self._result_sets: OrderedDict[str, tuple[UUID, list[UUID]]] = OrderedDict()
        self._lock = threading.Lock()

    def put(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> str:
        """Store sample IDs and return their new handle.

        Args:
            collection_id: The collection that the samples belong to.
            sample_ids: The sample IDs, in their result order.

        Returns:
            A unique handle for the result.
        """
        handle = f"result_{uuid.uuid4().hex}"
        with self._lock:
            self._result_sets[handle] = (collection_id, list(sample_ids))
            while len(self._result_sets) > self._max_result_sets:
                self._result_sets.popitem(last=False)
        return handle

    def get(self, collection_id: UUID, handle: str) -> list[UUID]:
        """Get the sample IDs of a handle.

        Args:
            collection_id: The collection that the samples must belong to.
            handle: The handle that ``put`` returned.

        Returns:
            The sample IDs, in their result order.

        Raises:
            ValueError: If the store does not know the handle for this collection.
        """
        with self._lock:
            entry = self._result_sets.get(handle)
        if entry is None or entry[0] != collection_id:
            raise ValueError(
                f"Unknown result handle {handle!r}. "
                "Find the samples again before using this result."
            )
        return list(entry[1])


# The store of the running server. Tools get it through `AgentContext`, so a test can pass
# its own store.
default_result_store = ResultStore()
