"""Tests for the settings resolver."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.settings import (
    GridViewSampleRenderingType,
    SettingView,
)
from lightly_studio.resolvers import settings_resolver


def test_get_settings_creates_default_settings(
    test_db: Session,
) -> None:
    """Test that get_settings creates default settings when none exist."""
    settings = settings_resolver.get_settings(session=test_db)

    assert settings is not None
    assert settings.grid_view_sample_rendering == GridViewSampleRenderingType.CONTAIN
    assert settings.show_sample_filenames is False


def test_set_settings_updates_grid_view_rendering(
    test_db: Session,
) -> None:
    """Test that set_settings updates the grid view rendering setting."""
    # First get settings to obtain a valid setting_id
    current_settings = settings_resolver.get_settings(session=test_db)

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
    )

    updated_settings = settings_resolver.set_settings(session=test_db, settings=input_settings)

    assert updated_settings is not None
    assert updated_settings.grid_view_sample_rendering == GridViewSampleRenderingType.CONTAIN
    assert updated_settings.show_sample_filenames is False
    assert updated_settings.key_hide_annotations == current_settings.key_hide_annotations
    assert updated_settings.key_go_back == current_settings.key_go_back
    assert (
        updated_settings.show_annotation_text_labels == current_settings.show_annotation_text_labels
    )

    settings = settings_resolver.get_settings(session=test_db)
    assert settings.grid_view_sample_rendering == GridViewSampleRenderingType.CONTAIN
    assert settings.show_sample_filenames is False
    assert settings.key_hide_annotations == current_settings.key_hide_annotations
    assert settings.key_go_back == current_settings.key_go_back
    assert settings.show_annotation_text_labels == current_settings.show_annotation_text_labels
