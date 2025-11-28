"""This module contains the resolvers for user settings."""

from sqlmodel import Session, select

from lightly_studio.models.settings import SettingTable, SettingView


def get_settings(session: Session) -> SettingView:
    """Get current settings.

    Args:
        session: Database session.

    Returns:
        The current settings.
    """
    statement = select(SettingTable)
    result = session.exec(statement).first()

    # If no settings exist, create default settings
    if result is None:
        result = SettingTable()
        session.add(result)
        session.commit()
        session.refresh(result)

    return SettingView.model_validate(result)


def set_settings(session: Session, settings: SettingView) -> SettingView:
    """Update settings.

    Args:
        session: Database session.
        settings: New settings to apply.

    Returns:
        Updated settings.
    """
    current_settings = session.exec(select(SettingTable)).first()
    if current_settings is None:
        current_settings = SettingTable()
        session.add(current_settings)

    # Update grid view sample rendering
    current_settings.grid_view_sample_rendering = settings.grid_view_sample_rendering

    # Update keyboard shortcut mapping
    current_settings.key_hide_annotations = settings.key_hide_annotations
    current_settings.key_go_back = settings.key_go_back
    current_settings.key_toggle_edit_mode = settings.key_toggle_edit_mode

    # Update show annotation text labels
    current_settings.show_annotation_text_labels = settings.show_annotation_text_labels

    # Update sample filename visibility
    current_settings.show_sample_filenames = settings.show_sample_filenames

    session.commit()
    session.refresh(current_settings)

    return SettingView.model_validate(current_settings)
