"""This module contains the FastAPI cache configuration for static files."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from os import PathLike, stat_result

from fastapi import Response
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from .routes.api.status import HTTP_STATUS_UNSUPPORTED_MEDIA_TYPE


class StaticFilesCache(StaticFiles):
    """StaticFiles class with cache headers."""

    days_to_expire = 1

    def __init__(  # noqa: PLR0913 (too-many-arguments)
        self,
        *,
        directory: str | PathLike[str] | None = None,
        packages: list[str | tuple[str, str]] | None = None,
        html: bool = False,
        check_dir: bool = True,
        follow_symlink: bool = False,
        cachecontrol: str | None = None,
    ) -> None:
        """Initialize the StaticFilesCache class."""
        self.cachecontrol = cachecontrol or f"private, max-age={self.days_to_expire * 24 * 60 * 60}"
        super().__init__(
            directory=directory,
            packages=packages,
            html=html,
            check_dir=check_dir,
            follow_symlink=follow_symlink,
        )

    def file_response(
        self,
        full_path: str | PathLike[str],
        stat_result: stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        """Override the file_response method to add cache headers."""
        allowed_extensions = (
            # Images
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".bmp",
            ".tiff",
            # Movies
            ".mov",
            ".mp4",
            ".avi",
        )

        if not str(full_path).lower().endswith(allowed_extensions):
            return Response(
                status_code=HTTP_STATUS_UNSUPPORTED_MEDIA_TYPE
            )  # Unsupported Media Type
        resp: Response = super().file_response(full_path, stat_result, scope, status_code)
        resp.headers.setdefault("Cache-Control", self.cachecontrol)

        # Calculate expiration date
        expire_date = datetime.now(timezone.utc) + timedelta(days=self.days_to_expire)
        resp.headers.setdefault("Expires", expire_date.strftime("%a, %d %b %Y %H:%M:%S GMT"))

        # Add Vary header to make sure caches respect the query parameters
        resp.headers.setdefault("Vary", "Accept-Encoding, Origin, v")

        return resp
