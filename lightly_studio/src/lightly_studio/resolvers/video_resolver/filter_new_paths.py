"""Implementation of filter_new_paths function for videos."""

from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.video import VideoTable


# TODO(Horatiu, 11/2025): Add collection_id parameter to support multiple collections.
def filter_new_paths(session: Session, file_paths_abs: list[str]) -> tuple[list[str], list[str]]:
    """Filter the file_paths into existing in DB and non existing in DB.

    Args:
        session: The database session.
        file_paths_abs: The file paths to filter.

    Returns:
        file_paths_abs that don't exist in the database,
        file_paths_abs that exist in the database
    """
    existing_file_paths_abs = set(
        session.exec(
            select(col(VideoTable.file_path_abs)).where(
                col(VideoTable.file_path_abs).in_(file_paths_abs)
            )
        ).all()
    )
    file_paths_abs_set = set(file_paths_abs)
    return (
        list(file_paths_abs_set - existing_file_paths_abs),  # paths that are not in the DB
        list(file_paths_abs_set & existing_file_paths_abs),  # paths that are in the DB
    )
