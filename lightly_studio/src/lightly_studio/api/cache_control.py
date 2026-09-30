"""Helper for building the Cache-Control header value of an API response."""

from __future__ import annotations


def cache_control(max_age_seconds: int, private: bool = False) -> str:
    """Builds a Cache-Control header value for an API response.

    Args:
        max_age_seconds: How long a client may reuse the response without revalidating, in
            seconds.
        private: If True, only the requesting user's browser may store the response and shared
            caches must not. Use for user-specific or access-controlled content.

    Returns:
        The Cache-Control header value, e.g. `private, max-age=60`.
    """
    visibility = "private" if private else "public"
    return f"{visibility}, max-age={max_age_seconds}"
