"""Tag field classes for building dataset queries on sample tags."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_
from sqlmodel import col

from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable


class TagsAccessor:
    """Provides access to tag operations for query building.

    This class enables checking tag membership using the contains method:
    ImageSampleField.tags.contains("tag_name") returns a TagsContainsExpression.
    Passing multiple names checks for all of the given tags:
    ImageSampleField.tags.contains(["tag_a", "tag_b"]).
    """

    def contains(self, tag_names: str | Iterable[str]) -> TagsContainsExpression:
        """Check if the sample has the given tag, or all of them if multiple are passed.

        Args:
            tag_names: The name of the tag to check for, or an iterable of tag names that
                must all be assigned to the sample.

        Returns:
            A TagsContainsExpression for building queries.

        Raises:
            ValueError: If no tag name is passed.
        """
        return TagsContainsExpression(tag_names=normalize_tag_names(tag_names))


@dataclass
class TagsContainsExpression(MatchExpression):
    """Expression for checking if a sample contains all of the given tags."""

    tag_names: tuple[str, ...]

    def get(self) -> ColumnElement[bool]:
        """Get the tag contains expression.

        Returns:
            The SQLAlchemy expression for this field expression.
        """
        return and_(
            *(SampleTable.tags.any(col(TagTable.name) == tag_name) for tag_name in self.tag_names)
        )


def normalize_tag_names(tag_names: str | Iterable[str]) -> tuple[str, ...]:
    """Normalize a single tag name or an iterable of tag names into a tuple.

    Args:
        tag_names: A single tag name or an iterable of tag names.

    Returns:
        The tag names as a tuple.

    Raises:
        ValueError: If no tag name is passed.
    """
    if isinstance(tag_names, str):
        return (tag_names,)
    names = tuple(tag_names)
    if len(names) == 0:
        raise ValueError("At least one tag name must be passed.")
    return names
