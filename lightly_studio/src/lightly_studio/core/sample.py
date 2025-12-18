"""Interface for Sample objects."""

from __future__ import annotations

from abc import ABC
from collections.abc import Iterable
from typing import Any, Generic, Protocol, TypeVar, cast
from uuid import UUID

from sqlalchemy.orm import Mapped, object_session
from sqlmodel import Session

from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import caption_resolver, metadata_resolver, tag_resolver

T = TypeVar("T")


class _DBFieldOwner(Protocol):
    inner: Any

    def get_object_session(self) -> Session: ...


class DBField(Generic[T]):
    """Descriptor for a database-backed field.

    Provides interface to a SQLAlchemy model field. Setting the field
    immediately commits to the database. The owner class must implement
    the inner attribute and the get_object_session() method.
    """

    __slots__ = ("_sqla_descriptor",)
    """Store the SQLAlchemy descriptor for accessing the field."""

    def __init__(self, sqla_descriptor: Mapped[T]) -> None:
        """Initialize the DBField with a SQLAlchemy descriptor."""
        self._sqla_descriptor = sqla_descriptor

    def __get__(self, obj: _DBFieldOwner | None, owner: type | None = None) -> T:
        """Get the value of the field from the database."""
        assert obj is not None, "DBField must be accessed via an instance, not the class"
        # Delegate to SQLAlchemy's descriptor.
        value: T = self._sqla_descriptor.__get__(obj.inner, type(obj.inner))
        return value

    def __set__(self, obj: _DBFieldOwner, value: T) -> None:
        """Set the value of the field in the database. Commits the session."""
        # Delegate to SQLAlchemy's descriptor.
        self._sqla_descriptor.__set__(obj.inner, value)
        obj.get_object_session().commit()


class Sample(ABC):
    """Interface to a dataset sample.

    It is usually returned by a query to the dataset.
    ```python
    for sample in dataset:
        ...
    ```

    Access sample's metadata via the `metadata` property, which
    provides a dictionary-like interface to get and set metadata key-value pairs.
    ```python
    some_value = sample.metadata["some_key"]
    sample.metadata["another_key"] = "new_value"
    ```

    Access sample's tags via the `tags` property.
    ```python
    sample.tags = ["tag1", "tag2"]  # Replace all tags
    print(f"Current tags: {sample.tags}")
    sample.add_tag("tag_3")
    sample.remove_tag("tag_1")
    ```
    """

    _sample_table: SampleTable

    @property
    def sample_id(self) -> UUID:
        """Sample ID."""
        return self._sample_table.sample_id

    def __init__(self, sample_table: SampleTable) -> None:
        """Initialize the Sample.

        Args:
            sample_table: The SampleTable SQLAlchemy model instance.
        """
        self._sample_table = sample_table
        self._metadata = SampleMetadata(self)

    @property
    def sample_table(self) -> SampleTable:
        """Returns the SampleTable associated with this Sample."""
        # TODO(lukas 12/2025): This should be later removed, as it exposes private implementation.
        # Remove this once we add a `annotations` property and `embeddings` property.
        return self._sample_table

    def get_object_session(self) -> Session:
        """Get the database session for this sample.

        Returns:
            The SQLModel session.

        Raises:
            RuntimeError: If no active session is found.
        """
        session = object_session(self._sample_table)
        if session is None:
            raise RuntimeError("No active session found for the sample")
        # Cast from SQLAlchemy Session to SQLModel Session for mypy.
        return cast(Session, session)

    def add_tag(self, name: str) -> None:
        """Add a tag to this sample.

        If the tag doesn't exist, it will be created first.

        Args:
            name: The name of the tag to add.
        """
        session = self.get_object_session()

        # Get or create the tag for this dataset.
        tag = tag_resolver.get_or_create_sample_tag_by_name(
            session=session, dataset_id=self.dataset_id, tag_name=name
        )

        # Add the tag to the sample if not already associated.
        if tag not in self.sample_table.tags:
            tag_resolver.add_tag_to_sample(
                session=session, tag_id=tag.tag_id, sample=self.sample_table
            )

    def remove_tag(self, name: str) -> None:
        """Remove a tag from this sample.

        Args:
            name: The name of the tag to remove.
        """
        session = self.get_object_session()

        # Find the tag by name for this dataset.
        existing_tag = tag_resolver.get_by_name(
            session=session, tag_name=name, dataset_id=self.dataset_id
        )

        # Remove the tag from the sample if it exists and is associated
        if existing_tag is not None and existing_tag in self.sample_table.tags:
            tag_resolver.remove_tag_from_sample(
                session=session, tag_id=existing_tag.tag_id, sample=self.sample_table
            )

    @property
    def tags(self) -> set[str]:
        """Get the tag names associated with this sample.

        Returns:
            A set of tag names as strings.
        """
        return {tag.name for tag in self.sample_table.tags}

    @tags.setter
    def tags(self, tags: Iterable[str]) -> None:
        """Set the tags for this sample, replacing any existing tags.

        Args:
            tags: Iterable of tag names to associate with this sample.
        """
        # Get current tag names
        current_tags = self.tags
        new_tags = set(tags)

        # Remove tags that are no longer needed
        tags_to_remove = current_tags - new_tags
        for tag_name in tags_to_remove:
            self.remove_tag(tag_name)

        # Add new tags
        tags_to_add = new_tags - current_tags
        for tag_name in tags_to_add:
            self.add_tag(tag_name)

    @property
    def metadata(self) -> SampleMetadata:
        """Get dictionary-like access to sample metadata.

        Returns:
            A dictionary-like object for accessing metadata.
        """
        return self._metadata

    @property
    def dataset_id(self) -> UUID:
        """Get the dataset ID this sample belongs to.

        Returns:
            The UUID of the dataset.
        """
        return self.sample_table.dataset_id

    def add_caption(self, text: str) -> None:
        """Add a caption to this sample.

        Args:
            text: The text of the caption to add.
        """
        session = self.get_object_session()
        caption_resolver.create_many(
            session=session,
            parent_collection_id=self.dataset_id,
            captions=[
                CaptionCreate(
                    parent_sample_id=self.sample_id,
                    text=text,
                ),
            ],
        )

    @property
    def captions(self) -> list[str]:
        """Returns the text of all captions."""
        return [caption.text for caption in self.sample_table.captions]

    @captions.setter
    def captions(self, captions: Iterable[str]) -> None:
        """Set the captions for this sample, replacing any existing captions.

        Args:
            captions: Iterable of caption texts to associate with this sample.
        """
        session = self.get_object_session()

        # Delete all existing captions for this sample
        caption_sample_ids = [c.sample_id for c in self.sample_table.captions]
        for caption_sample_id in caption_sample_ids:
            caption_resolver.delete_caption(session=session, sample_id=caption_sample_id)

        # Create new captions from the provided texts
        if captions:
            caption_resolver.create_many(
                session=session,
                parent_collection_id=self.dataset_id,
                captions=[
                    CaptionCreate(parent_sample_id=self.sample_id, text=text) for text in captions
                ],
            )


class SampleMetadata:
    """Dictionary-like interface for sample metadata."""

    def __init__(self, sample: Sample) -> None:
        """Initialize SampleMetadata.

        Args:
            sample: The Sample instance this metadata belongs to.
        """
        self._sample = sample

    def __getitem__(self, key: str) -> Any:
        """Get a metadata value by key.

        Args:
            key: The metadata key to access.

        Returns:
            The metadata value for the given key, or None if the key doesn't exist.
        """
        if self._sample.sample_table.metadata_dict is None:
            return None
        return self._sample.sample_table.metadata_dict.get_value(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a metadata key-value pair.

        Args:
            key: The metadata key.
            value: The metadata value.
        """
        session = self._sample.get_object_session()
        metadata_resolver.set_value_for_sample(
            session=session,
            sample_id=self._sample.sample_id,
            key=key,
            value=value,
        )
