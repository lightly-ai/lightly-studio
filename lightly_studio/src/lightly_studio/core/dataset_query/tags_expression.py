"""Tag field classes for building dataset queries on sample tags."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement
from sqlmodel import col

from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable


class TagsAccessor:
    """Provides access to tag operations for query building.

    This class enables checking tag membership using the contains method:
    ImageSampleField.tags.contains("tag_name") returns a TagsContainsExpression.
    """

    def contains(self, tag_name: str) -> TagsContainsExpression:
        """Check if a tag name is in the sample's tags.

        Args:
            tag_name: The name of the tag to check for.

        Returns:
            A TagsContainsExpression for building queries.
        """
        return TagsContainsExpression(tag_name=tag_name)


@dataclass
class TagsContainsExpression(MatchExpression):
    """Expression for checking if a sample contains a specific tag."""

    tag_name: str

    def get(self) -> ColumnElement[bool]:
        """Get the tag contains expression.

        Returns:
            The SQLAlchemy expression for this field expression.
        """
        return SampleTable.tags.any(col(TagTable.name) == self.tag_name)
