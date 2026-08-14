from pathlib import Path
from uuid import UUID

from lightly_studio.analytics import install_id


def test_get_install_id(tmp_path: Path) -> None:
    path = tmp_path / "install_id"

    result = install_id.get_install_id(path=path)

    assert UUID(path.read_text()) == result


def test_get_install_id__is_stable_across_calls(tmp_path: Path) -> None:
    path = tmp_path / "install_id"

    first = install_id.get_install_id(path=path)
    second = install_id.get_install_id(path=path)

    assert first == second


def test_get_install_id__creates_missing_directories(tmp_path: Path) -> None:
    path = tmp_path / "cache" / "lightly-studio" / "install_id"

    result = install_id.get_install_id(path=path)

    assert UUID(path.read_text()) == result


def test_get_install_id__replaces_unreadable_content(tmp_path: Path) -> None:
    path = tmp_path / "install_id"
    path.write_text("not a uuid")

    result = install_id.get_install_id(path=path)

    assert UUID(path.read_text()) == result


def test_get_install_id__when_the_path_cannot_be_written(tmp_path: Path) -> None:
    """A cache directory that cannot be written must still yield a usable ID."""
    # A file where a directory is expected makes both the read and the mkdir fail.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    path = blocker / "install_id"

    first = install_id.get_install_id(path=path)
    second = install_id.get_install_id(path=path)

    assert not path.exists()
    # Nothing was stored, so the ID cannot be stable across calls.
    assert first != second
