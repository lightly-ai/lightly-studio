"""Tests for the settings resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.settings import (
    GridViewSampleRenderingType,
    SettingView,
)
from lightly_studio.resolvers import settings_resolver


def test_get_settings_creates_default_settings(
    db_session: Session,
) -> None:
    """Test that get_settings creates default settings when none exist."""
    settings = settings_resolver.get_settings(session=db_session)

    assert settings is not None
    assert settings.grid_view_sample_rendering == GridViewSampleRenderingType.CONTAIN
    assert settings.show_annotation_text_labels is False
    assert settings.show_sample_filenames is False
    assert settings.show_bounding_boxes_for_segmentation is True
    assert settings.key_toolbar_brush == "r"
    assert settings.key_toolbar_eraser == "x"


def test_set_settings_updates_grid_view_rendering(
    db_session: Session,
) -> None:
    """Test that set_settings updates the grid view rendering setting."""
    # First get settings to obtain a valid setting_id
    current_settings = settings_resolver.get_settings(session=db_session)

    # Include the required datetime fields
    input_settings = SettingView(
        setting_id=current_settings.setting_id,
        grid_view_sample_rendering=GridViewSampleRenderingType.CONTAIN,
        created_at=current_settings.created_at,
        updated_at=current_settings.updated_at,
        key_hide_annotations=current_settings.key_hide_annotations,
        key_go_back=current_settings.key_go_back,
        show_annotation_text_labels=current_settings.show_annotation_text_labels,
        show_sample_filenames=False,
        show_bounding_boxes_for_segmentation=False,
        key_toolbar_selection="d",
        key_toolbar_drag="s",
        key_toolbar_bounding_box="m",
        key_toolbar_segmentation_mask="b",
        key_toolbar_brush="r",
        key_toolbar_eraser="x",
    )

    updated_settings = settings_resolver.set_settings(session=db_session, settings=input_settings)

    assert updated_settings is not None
    assert updated_settings.grid_view_sample_rendering == GridViewSampleRenderingType.CONTAIN
    assert updated_settings.show_sample_filenames is False
    assert updated_settings.key_hide_annotations == current_settings.key_hide_annotations
    assert updated_settings.key_go_back == current_settings.key_go_back
    assert (
        updated_settings.show_annotation_text_labels == current_settings.show_annotation_text_labels
    )
    assert updated_settings.show_bounding_boxes_for_segmentation is False
    assert updated_settings.key_toolbar_selection == "d"
    assert updated_settings.key_toolbar_drag == "s"
    assert updated_settings.key_toolbar_bounding_box == "m"
    assert updated_settings.key_toolbar_segmentation_mask == "b"
    assert updated_settings.key_toolbar_brush == "r"
    assert updated_settings.key_toolbar_eraser == "x"

    settings = settings_resolver.get_settings(session=db_session)
    assert settings.grid_view_sample_rendering == GridViewSampleRenderingType.CONTAIN
    assert settings.show_sample_filenames is False
    assert settings.key_hide_annotations == current_settings.key_hide_annotations
    assert settings.key_go_back == current_settings.key_go_back
    assert settings.show_annotation_text_labels == current_settings.show_annotation_text_labels
    assert settings.show_bounding_boxes_for_segmentation is False
    assert settings.key_toolbar_brush == "r"
    assert settings.key_toolbar_eraser == "x"
