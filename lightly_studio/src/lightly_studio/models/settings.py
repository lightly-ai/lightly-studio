"""This module contains settings model for user preferences."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from lightly_studio.models.db_enum import enum_column


class GridViewSampleRenderingType(str, Enum):
    """Defines how samples are rendered in the grid view."""

    COVER = "cover"
    CONTAIN = "contain"


class GridViewThumbnailQualityType(str, Enum):
    """Defines how thumbnails are fetched for grid-like views."""

    RAW = "raw"
    HIGH = "high"


class SettingBase(SQLModel):
    """Base class for Settings model."""

    grid_view_sample_rendering: GridViewSampleRenderingType = Field(
        sa_column=enum_column(GridViewSampleRenderingType),
        description="Controls how samples are rendered in the grid view",
    )
    grid_view_thumbnail_quality: GridViewThumbnailQualityType = Field(
        sa_column=enum_column(GridViewThumbnailQualityType),
        description="Controls thumbnail quality for grid-like preview views",
    )

    # Keyboard shortcuts.
    key_hide_annotations: str = Field(
        description="Key to temporarily hide annotations while pressed",
    )
    key_go_back: str = Field(
        description="Key to navigate back from detail view to grid view",
    )
    key_toggle_edit_mode: str = Field(
        description="Key to toggle annotation edit mode",
    )

    show_annotation_text_labels: bool = Field(
        description="Controls whether to show text labels on annotations",
    )

    show_sample_filenames: bool = Field(
        description="Controls whether to show sample filenames in the samples grid view",
    )

    show_bounding_boxes_for_segmentation: bool = Field(
        description="Controls whether to show annotation bounding boxes for segmentation",
    )

    # Toolbar shortcuts
    key_toolbar_selection: str = Field(
        description="Key to activate the selection tool in the toolbar",
    )
    key_toolbar_drag: str = Field(
        description="Key to activate the drag tool in the toolbar",
    )
    key_toolbar_bounding_box: str = Field(
        description="Key to activate the bounding box tool in the toolbar",
    )
    key_toolbar_segmentation_mask: str = Field(
        description="Key to activate the segmentation mask tool in the toolbar",
    )
    key_toolbar_brush: str = Field(
        description="Key to activate brush mode in the segmentation tool",
    )
    key_toolbar_eraser: str = Field(
        description="Key to activate eraser mode in the segmentation tool",
    )


class SettingDefaults(SettingBase):
    """Settings fields with defaults for database inserts."""

    grid_view_sample_rendering: GridViewSampleRenderingType = Field(
        default=GridViewSampleRenderingType.CONTAIN,
        sa_column=enum_column(GridViewSampleRenderingType),
    )
    grid_view_thumbnail_quality: GridViewThumbnailQualityType = Field(
        default=GridViewThumbnailQualityType.RAW,
        sa_column=enum_column(GridViewThumbnailQualityType),
    )
    key_hide_annotations: str = Field(
        default="v",
    )
    key_go_back: str = Field(
        default="Escape",
    )
    key_toggle_edit_mode: str = Field(
        default="e",
    )
    show_annotation_text_labels: bool = Field(
        default=False,
    )
    show_sample_filenames: bool = Field(
        default=False,
    )
    show_bounding_boxes_for_segmentation: bool = Field(
        default=True,
    )
    key_toolbar_selection: str = Field(
        default="s",
    )
    key_toolbar_drag: str = Field(
        default="d",
    )
    key_toolbar_bounding_box: str = Field(
        default="b",
    )
    key_toolbar_segmentation_mask: str = Field(
        default="m",
    )
    key_toolbar_brush: str = Field(
        default="r",
    )
    key_toolbar_eraser: str = Field(
        default="x",
    )


class SettingView(SettingBase):
    """View class for Settings model."""

    setting_id: UUID
    created_at: datetime
    updated_at: datetime


class SettingTable(SettingDefaults, table=True):
    """This class defines the Setting model."""

    __tablename__ = "setting"
    setting_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
