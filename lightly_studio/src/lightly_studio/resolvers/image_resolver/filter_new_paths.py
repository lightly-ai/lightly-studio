"""Implementation of filter_new_paths function for images."""

from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.image import ImageTable


def filter_new_paths(session: Session, file_paths_abs: list[str]) -> tuple[list[str], list[str]]:
    """Return a) file_path_abs that do not already exist in the database and b) those that do."""
    existing_file_paths_abs = set(
        session.exec(
            select(col(ImageTable.file_path_abs)).where(
                col(ImageTable.file_path_abs).in_(file_paths_abs)
            )
        ).all()
    )
    file_paths_abs_set = set(file_paths_abs)
    return (
        list(file_paths_abs_set - existing_file_paths_abs),  # paths that are not in the DB
        list(file_paths_abs_set & existing_file_paths_abs),  # paths that are already in the DB
    )
