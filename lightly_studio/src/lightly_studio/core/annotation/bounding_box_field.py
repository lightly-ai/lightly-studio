"""Bounding box coordinate descriptor."""

from __future__ import annotations

import dataclasses
from typing import Any, Protocol

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates
from lightly_studio.transport import active_transport


class BoundingBoxField:
    """Descriptor for one coordinate of the bounding box of an annotation.

    Setting the coordinate updates the annotation through the active transport.
    """

    def __set_name__(self, owner: type, name: str) -> None:
        """Store the name of the coordinate."""
        self._name = name

    def __get__(self, obj: _BoundingBoxOwner | None, owner: type | None = None) -> int:
        """Get the coordinate."""
        if obj is None:
            raise RuntimeError("BoundingBoxField must be accessed via an instance, not the class")
        value: int = getattr(obj.inner, self._name)
        return value

    def __set__(self, obj: _BoundingBoxOwner, value: int) -> None:
        """Set the coordinate. Keep the other coordinates."""
        inner = obj.inner
        bounding_box = BoundingBoxCoordinates(
            x=inner.x, y=inner.y, width=inner.width, height=inner.height
        )
        active_transport.get_transport().annotations.update_bounding_box(
            annotation_id=obj.annotation_base.sample_id,
            bounding_box=dataclasses.replace(bounding_box, **{self._name: value}),
        )


class _BoundingBoxOwner(Protocol):
    inner: Any
    annotation_base: AnnotationBaseTable
