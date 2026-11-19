"""Image sample with the plain data of a sample query, without a database session."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NoReturn
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.core.sample import SampleMetadata
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_query import ImageSampleRecord
from lightly_studio.transport.tag_transport import TagTransport


class RecordImageSample(ImageSample):
    """Image sample from a query through the transport.

    It reads the image fields and the tags of the query result. `add_tag` and `remove_tag`
    call the transport. Other data and all other writes raise `NotImplementedError`.
    """

    def __init__(self, record: ImageSampleRecord, tag_transport: TagTransport) -> None:
        """Create the sample from a query result.

        Args:
            record: The sample data. It must include the tags.
            tag_transport: The transport that adds and removes tags.
        """
        if record.tags is None:
            raise ValueError("The sample record must include the tags.")
        # A detached row, so that the image fields of `ImageSample` read the record.
        self.inner = ImageTable(**record.model_dump(exclude={"collection_id", "tags"}))
        self._record = record
        self._tags = set(record.tags)
        self._tag_transport = tag_transport

    @property
    def sample_table(self) -> SampleTable:
        """Not supported for samples from the transport."""
        _raise_not_supported()

    @property
    def sample_id(self) -> UUID:
        """Sample ID."""
        return self._record.sample_id

    @property
    def collection_id(self) -> UUID:
        """The ID of the collection of the sample."""
        return self._record.collection_id

    @property
    def metadata(self) -> SampleMetadata:
        """Not supported for samples from the transport yet."""
        _raise_not_supported()

    @property
    def tags(self) -> set[str]:
        """The tag names of the sample."""
        return set(self._tags)

    @tags.setter
    def tags(self, tags: Iterable[str]) -> None:
        current_tags = self.tags
        new_tags = set(tags)
        for name in current_tags - new_tags:
            self.remove_tag(name)
        for name in new_tags - current_tags:
            self.add_tag(name)

    def get_object_session(self) -> Session:
        """Not supported for samples from the transport. Writes need a session."""
        _raise_not_supported()

    def add_tag(self, name: str) -> None:
        """Add a tag to this sample. Create the tag if it does not exist."""
        self._tag_transport.add_to_samples(
            collection_id=self.collection_id, tag_name=name, sample_ids=[self.sample_id]
        )
        self._tags.add(name)

    def remove_tag(self, name: str) -> None:
        """Remove a tag from this sample."""
        self._tag_transport.remove_from_samples(
            collection_id=self.collection_id, tag_name=name, sample_ids=[self.sample_id]
        )
        self._tags.discard(name)


def _raise_not_supported() -> NoReturn:
    raise NotImplementedError("This is not supported for samples from a remote query yet.")
