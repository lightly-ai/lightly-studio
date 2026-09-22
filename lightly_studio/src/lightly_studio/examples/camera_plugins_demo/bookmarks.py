"""Save camera frames as image samples in a LightlyStudio dataset."""

from __future__ import annotations

import collections
import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import cv2

from lightly_studio.core.image.create_image import CreateImage
from lightly_studio.database import db_manager
from lightly_studio.embed import embed_samples
from lightly_studio.examples.camera_plugins_demo.camera import Frame
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.metadata_resolver import sample as sample_metadata_resolver

logger = logging.getLogger(__name__)

_RECENT_SIZE = 12
_JPEG_QUALITY = 95


@dataclass(frozen=True)
class Bookmark:
    """A camera frame saved as an image sample.

    Attributes:
        sample_id: ID of the image sample in LightlyStudio.
        file_name: Name of the JPEG file in the bookmarks directory.
        tags: Tags assigned to the sample.
        captured_at: Local time of the capture.
    """

    sample_id: UUID
    file_name: str
    tags: tuple[str, ...]
    captured_at: datetime


class BookmarkStore:
    """Writes bookmarked frames to disk and adds them to a LightlyStudio dataset.

    LightlyStudio reads images from their file path, so the JPEG files must stay in
    `bookmarks_dir`. Each call uses its own short-lived database session, which makes
    it safe to call from web request threads while the LightlyStudio GUI is running.
    """

    def __init__(
        self,
        bookmarks_dir: Path,
        collection_id: UUID,
        camera_name: str,
        embed: bool,
    ) -> None:
        """Create the store and its bookmarks directory."""
        self.bookmarks_dir = bookmarks_dir
        self._collection_id = collection_id
        self._camera_name = camera_name
        self._embed = embed
        self._lock = threading.Lock()
        self._recent: collections.deque[Bookmark] = collections.deque(maxlen=_RECENT_SIZE)
        self.bookmarks_dir.mkdir(parents=True, exist_ok=True)

    def add(self, frame: Frame, tags: Sequence[str], capture: str) -> Bookmark:
        """Save a frame and add it to the dataset as an image sample.

        Args:
            frame: The camera frame to save.
            tags: Tags to assign to the new sample. Empty strings are ignored.
            capture: How the frame was captured, for example "manual". Stored in the
                sample metadata so the grid can filter by it.

        Returns:
            The new bookmark.
        """
        captured_at = datetime.fromtimestamp(frame.timestamp, tz=timezone.utc).astimezone()
        file_name = f"frame_{captured_at:%Y%m%d_%H%M%S_%f}.jpg"
        path = self.bookmarks_dir / file_name
        if not cv2.imwrite(str(path), frame.image, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY]):
            raise OSError(f"Failed to write '{path}'.")

        clean_tags = tuple(tag.strip() for tag in tags if tag.strip())
        with self._lock, db_manager.session() as session:
            sample_id = CreateImage(path=str(path)).create_in_collection(
                session=session, collection_id=self._collection_id
            )
            for tag_name in clean_tags:
                tag = tag_resolver.get_or_create_sample_tag_by_name(
                    session=session, collection_id=self._collection_id, tag_name=tag_name
                )
                tag_resolver.add_sample_ids_to_tag_id(
                    session=session, tag_id=tag.tag_id, sample_ids=[sample_id]
                )
            sample_metadata_resolver.bulk_update_metadata(
                session=session,
                sample_metadata=[(sample_id, {"capture": capture, "camera": self._camera_name})],
            )
            if self._embed:
                try:
                    embed_samples.embed_image_samples(
                        session=session, collection_id=self._collection_id, sample_ids=[sample_id]
                    )
                except Exception:
                    # A missing embedding only disables similarity search for this image.
                    logger.exception("Failed to embed bookmark %s.", file_name)

        bookmark = Bookmark(
            sample_id=sample_id, file_name=file_name, tags=clean_tags, captured_at=captured_at
        )
        self._recent.appendleft(bookmark)
        logger.info("Bookmarked %s (tags: %s)", file_name, ", ".join(clean_tags) or "none")
        return bookmark

    def recent(self) -> list[Bookmark]:
        """Return the most recent bookmarks of this session, newest first."""
        return list(self._recent)

    def count(self) -> int:
        """Return the number of bookmarked frames on disk."""
        return sum(1 for _ in self.bookmarks_dir.glob("frame_*.jpg"))
