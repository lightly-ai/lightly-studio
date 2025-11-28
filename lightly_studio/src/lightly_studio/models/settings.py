"""This module contains settings model for user preferences."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class GridViewSampleRenderingType(str, Enum):
    """Defines how samples are rendered in the grid view."""

    COVER = "cover"
    CONTAIN = "contain"


class SettingBase(SQLModel):
    """Base class for Settings model."""

    grid_view_sample_rendering: GridViewSampleRenderingType = Field(
        default=GridViewSampleRenderingType.CONTAIN,
        description="Controls how samples are rendered in the grid view",
    )

    # Keyboard shortcuts.
    key_hide_annotations: str = Field(
        default="v",
        description="Key to temporarily hide annotations while pressed",
    )
    key_go_back: str = Field(
        default="Escape",
        description="Key to navigate back from detail view to grid view",
    )
    key_toggle_edit_mode: str = Field(
        default="e",
        description="Key to toggle annotation edit mode",
    )

    # New setting for annotation text visibility.
    show_annotation_text_labels: bool = Field(
        default=True,
        description="Controls whether to show text labels on annotations",
    )

    show_sample_filenames: bool = Field(
        default=False,
        description="Controls whether to show sample filenames in the samples grid view",
    )


class SettingView(SettingBase):
    """View class for Settings model."""

    setting_id: UUID
    created_at: datetime
    updated_at: datetime


class SettingTable(SettingBase, table=True):
    """This class defines the Setting model."""

    __tablename__ = "setting"
    setting_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
