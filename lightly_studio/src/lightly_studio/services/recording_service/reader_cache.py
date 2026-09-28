"""Process-wide MCAP reader cache used by recording media services."""

from __future__ import annotations

import os
import threading
from collections import OrderedDict

import fsspec.utils

from lightly_studio.core.mcap.reader import McapFileReader, ReadPattern

_READER_CACHE_SIZE = 4
_REMOTE_PROTOCOLS = {"s3", "gs", "gcs"}

# One reader per recording for all request threads, so that its read cache serves every
# request, e.g. the point clouds of several lidars at one tick with one fetch. The reader
# serializes its own reads.
_readers: OrderedDict[str, McapFileReader] = OrderedDict()
_readers_lock = threading.Lock()


def get_cached_reader(uri: str) -> McapFileReader:
    """Return the shared random-access reader for an MCAP URI.

    Keeps up to `_READER_CACHE_SIZE` readers open and closes the least recently used one
    on overflow.
    """
    with _readers_lock:
        if uri in _readers:
            _readers.move_to_end(uri)
            return _readers[uri]
        reader = McapFileReader(
            uri, storage_options=_storage_options(uri=uri), read_pattern=ReadPattern.RANDOM
        )
        _readers[uri] = reader
        while len(_readers) > _READER_CACHE_SIZE:
            _, evicted = _readers.popitem(last=False)
            evicted.close()
        return reader


def clear() -> None:
    """Close and forget all cached readers."""
    with _readers_lock:
        for reader in _readers.values():
            reader.close()
        _readers.clear()


def _storage_options(uri: str) -> dict[str, object] | None:
    """Return the fsspec options for a URI, pointing S3 to the endpoint from the environment."""
    if fsspec.utils.get_protocol(uri) not in _REMOTE_PROTOCOLS:
        return None
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint_url:
        return None
    return {"client_kwargs": {"endpoint_url": endpoint_url}}
