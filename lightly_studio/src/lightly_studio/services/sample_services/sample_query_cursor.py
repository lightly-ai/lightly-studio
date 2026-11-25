"""Opaque cursor for keyset paging of the sample query.

The cursor is base64url JSON: `{"v": 1, "q": <query hash>, "after": [<sort values>]}`.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from lightly_studio.models.sample_query import SampleQueryRequest

_VERSION = 1
_HASH_LENGTH = 16


def query_hash(collection_id: UUID, request: SampleQueryRequest) -> str:
    """Get a short hash of the collection, the filter and the sort of a request.

    Args:
        collection_id: The ID of the queried collection.
        request: The query request. Only the filter and the sort change the hash.

    Returns:
        A hex string of 16 characters.
    """
    scope = {
        "collection_id": str(collection_id),
        **request.model_dump(mode="json", include={"query_expr", "sort"}),
    }
    canonical = json.dumps(scope, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:_HASH_LENGTH]


def encode(query_hash: str, after: Sequence[Any]) -> str:
    """Encode the sort values of the last sample of a page as a cursor.

    Args:
        query_hash: The hash of the query, from `query_hash`.
        after: The sort values of the last sample, then its sample ID.

    Returns:
        The cursor as unpadded base64url text.
    """
    payload = {"v": _VERSION, "q": query_hash, "after": list(after)}
    text = json.dumps(payload, separators=(",", ":"), default=_to_json)
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def decode(cursor: str, query_hash: str) -> list[Any]:
    """Decode the sort values of a cursor.

    Args:
        cursor: The cursor from `encode`.
        query_hash: The hash of the current query. It must match the hash in the cursor.

    Returns:
        The sort values as JSON values. Datetimes and UUIDs are strings.

    Raises:
        ValueError: If the cursor is not valid or belongs to a different query.
    """
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.b64decode(padded, altchars=b"-_", validate=True))
    except (binascii.Error, RecursionError, UnicodeDecodeError, ValueError) as error:
        raise ValueError("The cursor is not valid.") from error
    if not isinstance(payload, dict) or payload.get("v") != _VERSION:
        raise ValueError("The cursor is not valid.")
    if payload.get("q") != query_hash:
        raise ValueError("The cursor belongs to a different query.")
    after = payload.get("after")
    if not isinstance(after, list):
        raise ValueError("The cursor is not valid.")
    return after


def _to_json(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Cannot encode {type(value).__name__} in a cursor.")
