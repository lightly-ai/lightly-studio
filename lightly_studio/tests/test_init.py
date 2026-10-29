from __future__ import annotations

import lightly_studio as ls


def test_all__exports_documented_modules() -> None:
    # Type checkers such as Pylance flag `ls.utils.download_example_dataset(...)` if a
    # module is not in `__all__`.
    assert "utils" in ls.__all__
    assert "db_manager" in ls.__all__


def test_all__names_exist() -> None:
    missing = [name for name in ls.__all__ if not hasattr(ls, name)]

    assert missing == []
