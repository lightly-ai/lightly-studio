"""Process-wide pool of open MCAP readers.

A reader has one file position, so a request checks a reader out and returns it
when it finishes. The next request reuses the open reader and does not resolve
credentials or read the file header again. Parallel requests for one recording
get different readers, up to a cap.
"""

from __future__ import annotations

import os
import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager

import fsspec.utils

from lightly_studio.core.mcap.reader import McapFileReader, ReadPattern

# A page reads several channels at once. Eight readers cover that page, and eight
# idle readers keep the recordings on screen open.
_MAX_READERS_PER_URI = 8
_MAX_IDLE_READERS = 8
_REMOTE_PROTOCOLS = frozenset({"s3", "gs", "gcs"})

_lock = threading.Lock()


class _Slot:
    """The open readers of one URI."""

    def __init__(self) -> None:
        """Starts an empty slot."""
        self.idle: list[McapFileReader] = []
        self.opened = 0
        self.available = threading.Condition(_lock)


_slots: OrderedDict[str, _Slot] = OrderedDict()


@contextmanager
def borrow_reader(uri: str) -> Iterator[McapFileReader]:
    """Checks out an open reader and returns it when the caller is done.

    Args:
        uri: The URI of the recording's MCAP file.

    Yields:
        A reader positioned for a new request. The caller does not close it.
    """
    reader = _checkout(uri=uri)
    try:
        yield reader
    finally:
        _checkin(uri=uri, reader=reader)


def clear() -> None:
    """Closes idle readers and drops the pool.

    A reader that is checked out is closed when it is returned.
    """
    with _lock:
        slots = list(_slots.values())
        idle = [reader for slot in slots for reader in slot.idle]
        for slot in slots:
            slot.idle.clear()
            slot.opened = 0
            slot.available.notify_all()
        _slots.clear()
    for reader in idle:
        reader.close()


def _checkout(uri: str) -> McapFileReader:
    """Returns an idle reader, or opens one while fewer than the cap are open."""
    while True:
        with _lock:
            slot = _slot_for(uri=uri)
            if slot.idle:
                return slot.idle.pop()
            if slot.opened < _MAX_READERS_PER_URI:
                slot.opened += 1
                opening = True
            else:
                opening = False
                slot.available.wait()
        if opening:
            return _open_or_release(uri=uri, slot=slot)


def _slot_for(uri: str) -> _Slot:
    """Returns the slot of a URI, creating it. The caller holds `_lock`."""
    slot = _slots.get(uri)
    if slot is None:
        slot = _Slot()
        _slots[uri] = slot
    _slots.move_to_end(uri)
    return slot


def _open_or_release(uri: str, slot: _Slot) -> McapFileReader:
    """Opens a reader, and releases the reserved slot when opening fails."""
    try:
        return _open_reader(uri=uri)
    except Exception:
        with _lock:
            if slot.opened > 0:
                slot.opened -= 1
            slot.available.notify()
        raise


def _checkin(uri: str, reader: McapFileReader) -> None:
    """Returns a reader to its slot and closes the least recently used extras."""
    extras: list[McapFileReader] = []
    with _lock:
        slot = _slots.get(uri)
        if slot is None:
            extras.append(reader)
        else:
            slot.idle.append(reader)
            _slots.move_to_end(uri)
            extras.extend(_take_excess_idle())
            slot.available.notify()
    for extra in extras:
        extra.close()


def _open_reader(uri: str) -> McapFileReader:
    """Opens a random-access reader for a URI."""
    return McapFileReader(
        path=uri,
        storage_options=_storage_options(uri=uri),
        read_pattern=ReadPattern.RANDOM,
    )


def _storage_options(uri: str) -> dict[str, object] | None:
    """Returns the fsspec options a remote URI needs, or `None` for a local path."""
    if fsspec.utils.get_protocol(uri) not in _REMOTE_PROTOCOLS:
        return None
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint_url:
        return None
    return {"client_kwargs": {"endpoint_url": endpoint_url}}


def _take_excess_idle() -> list[McapFileReader]:
    """Removes idle readers past the cap. The caller holds `_lock`."""
    extras: list[McapFileReader] = []
    while _idle_count() > _MAX_IDLE_READERS:
        oldest = _pop_oldest_idle()
        if oldest is None:
            break
        extras.append(oldest)
    return extras


def _idle_count() -> int:
    """Returns how many readers are waiting to be reused. The caller holds `_lock`."""
    return sum(len(slot.idle) for slot in _slots.values())


def _pop_oldest_idle() -> McapFileReader | None:
    """Removes the idle reader that was returned least recently. The caller holds `_lock`.

    A slot with no open reader left is dropped, so the pool does not keep one slot
    for every URI it has ever opened.
    """
    for uri, slot in _slots.items():
        if not slot.idle:
            continue
        oldest = slot.idle.pop(0)
        slot.opened -= 1
        slot.available.notify()
        if slot.opened == 0:
            del _slots[uri]
        return oldest
    return None
