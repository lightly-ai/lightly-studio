"""Actions that the GUI applies after an agent turn.

A tool cannot change the GUI directly. It records an action, and the GUI applies the
actions of a turn in their order when the answer arrives.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SelectTagAction(BaseModel):
    """Reload the tags and filter the grid to one tag."""

    type: Literal["select_tag"] = "select_tag"
    tag_id: UUID
    tag_name: str


class ShowSamplesAction(BaseModel):
    """Filter the grid to a list of samples."""

    type: Literal["show_samples"] = "show_samples"
    sample_ids: list[UUID]


class RefreshDataAction(BaseModel):
    """Reload the tags and the samples, because a tool changed data that the GUI shows."""

    type: Literal["refresh_data"] = "refresh_data"


UiAction = Annotated[
    SelectTagAction | ShowSamplesAction | RefreshDataAction, Field(discriminator="type")
]
