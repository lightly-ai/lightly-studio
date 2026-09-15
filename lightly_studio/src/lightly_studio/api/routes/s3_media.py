"""Helpers for redirecting eligible media requests to Amazon S3."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, cast

import fsspec
from fastapi.responses import RedirectResponse

from lightly_studio.dataset import env
from lightly_studio.utils import executor

NO_STORE_CACHE_CONTROL = "private, no-store"


class MediaDeliveryMode(str, Enum):
    """Explicit media-delivery overrides accepted by media routes."""

    PROXY = "proxy"


async def create_s3_media_redirect(
    file_path: str,
    content_type: str,
) -> RedirectResponse | None:
    """Create an uncached redirect for an S3 object when the POC is enabled.

    Returns None for ineligible paths and signing failures so the caller can
    retain proxy delivery for that request.
    """
    if not env.LIGHTLY_STUDIO_MEDIA_DIRECT_URLS:
        return None
    if fsspec.utils.get_protocol(file_path) != "s3":
        return None

    try:
        url = await asyncio.get_running_loop().run_in_executor(
            executor.get_media_executor("s3_media_signing"),
            _sign_s3_media_url,
            file_path,
            content_type,
            env.LIGHTLY_STUDIO_MEDIA_DIRECT_URL_TTL_SECONDS,
        )
    except Exception:
        return None

    return RedirectResponse(
        url=url,
        status_code=307,
        headers={"Cache-Control": NO_STORE_CACHE_CONTROL},
    )


def _sign_s3_media_url(file_path: str, content_type: str, expiration: int) -> str:
    """Sign an S3 GET request using fsspec's configured credential provider."""
    fs, fs_path = fsspec.core.url_to_fs(url=file_path, cache_regions=True)
    signer = cast(Any, fs)
    return cast(
        str,
        signer.sign(
            fs_path,
            expiration=expiration,
            ResponseContentType=content_type,
            ResponseCacheControl=NO_STORE_CACHE_CONTROL,
        ),
    )
