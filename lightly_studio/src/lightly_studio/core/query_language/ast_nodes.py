"""AST node types for the query language."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class ComparisonNode(BaseModel):
    """A leaf comparison: field op value."""

    node_type: Literal["comparison"] = "comparison"
    field: list[str]
    operator: str
    value: Any


class AndNode(BaseModel):
    """Logical AND of two or more sub-expressions."""

    node_type: Literal["and"] = "and"
    children: list[QueryNode]


class OrNode(BaseModel):
    """Logical OR of two or more sub-expressions."""

    node_type: Literal["or"] = "or"
    children: list[QueryNode]


class NotNode(BaseModel):
    """Logical NOT of a sub-expression."""

    node_type: Literal["not"] = "not"
    child: QueryNode


class HasTagNode(BaseModel):
    """Checks that a sample has a specific tag."""

    node_type: Literal["has_tag"] = "has_tag"
    tag_name: str


class HasAnnotationNode(BaseModel):
    """Checks that a sample has at least one annotation matching an inner query."""

    node_type: Literal["has_annotation"] = "has_annotation"
    inner: QueryNode


QueryNode = Annotated[
    Union[
        ComparisonNode,
        AndNode,
        OrNode,
        NotNode,
        HasTagNode,
        HasAnnotationNode,
    ],
    Field(discriminator="node_type"),
]

# Resolve forward references for models that contain QueryNode fields.
AndNode.model_rebuild()
OrNode.model_rebuild()
NotNode.model_rebuild()
HasAnnotationNode.model_rebuild()
