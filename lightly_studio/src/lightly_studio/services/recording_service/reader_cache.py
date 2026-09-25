"""Thread-local MCAP reader cache used by recording media services."""

from __future__ import annotations

import os
import threading
from collections import OrderedDict

import fsspec.utils

from lightly_studio.core.mcap.reader import McapFileReader, ReadPattern

_thread_local = threading.local()
_READER_CACHE_SIZE = 4
_REMOTE_PROTOCOLS = {"s3", "gs", "gcs"}


def get_cached_reader(uri: str) -> McapFileReader:
    """Return a cached random-access reader for an MCAP URI."""
    if not hasattr(_thread_local, "reader_cache"):
        _thread_local.reader_cache = OrderedDict()
    cache: OrderedDict[str, McapFileReader] = _thread_local.reader_cache
    if uri in cache:
        cache.move_to_end(uri)
        return cache[uri]
    protocol = fsspec.utils.get_protocol(uri)
    storage_options: dict[str, object] | None = None
    if protocol in _REMOTE_PROTOCOLS:
        endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
        if endpoint_url:
            storage_options = {"client_kwargs": {"endpoint_url": endpoint_url}}
    reader = McapFileReader(uri, storage_options=storage_options, read_pattern=ReadPattern.RANDOM)
    cache[uri] = reader
    while len(cache) > _READER_CACHE_SIZE:
        _, evicted = cache.popitem(last=False)
        evicted.close()
    return reader
