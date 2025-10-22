"""Interface for Sample objects."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Generic, Protocol, TypeVar, cast

from sqlalchemy.orm import Mapped, object_session
from sqlmodel import Session, col

from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import metadata_resolver, tag_resolver

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


class Sample:
    """Interface to a dataset sample.

    It is usually returned by a query to the dataset.
    ```python
    for sample in dataset:
        ...
    ```

    Many properties of the sample are directly accessible as attributes of this class.
    ```python
    print(f"Sample file name: {sample.file_name}")
    print(f"Sample file path: {sample.file_path_abs}")
    print(f"Sample width: {sample.width}")
    print(f"Sample height: {sample.height}")
    ```
    Note that some attributes like the `sample_id` are technically writable, but changing
    them is not recommended and may lead to inconsistent states.

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

    file_name = DBField(col(ImageTable.file_name))
    width = DBField(col(ImageTable.width))
    height = DBField(col(ImageTable.height))
    dataset_id = DBField(col(ImageTable.dataset_id))
    file_path_abs = DBField(col(ImageTable.file_path_abs))

    sample_id = DBField(col(ImageTable.sample_id))
    created_at = DBField(col(ImageTable.created_at))
    updated_at = DBField(col(ImageTable.updated_at))

    def __init__(self, inner: ImageTable) -> None:
        """Initialize the Sample.

        Args:
            inner: The ImageTable SQLAlchemy model instance.
        """
        self.inner = inner
        self._metadata = SampleMetadata(self)

    def get_object_session(self) -> Session:
        """Get the database session for this sample.

        Returns:
            The SQLModel session.

        Raises:
            RuntimeError: If no active session is found.
        """
        session = object_session(self.inner)
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
        if tag not in self.inner.sample.tags:
            tag_resolver.add_tag_to_sample(session=session, tag_id=tag.tag_id, sample=self.inner.sample)

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
        if existing_tag is not None and existing_tag in self.inner.sample.tags:
            tag_resolver.remove_tag_from_sample(
                session=session, tag_id=existing_tag.tag_id, sample=self.inner.sample
            )

    @property
    def tags(self) -> set[str]:
        """Get the tag names associated with this sample.

        Returns:
            A set of tag names as strings.
        """
        return {tag.name for tag in self.inner.sample.tags}

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
        if self._sample.inner.metadata_dict is None:
            return None
        return self._sample.inner.metadata_dict.get_value(key)

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
