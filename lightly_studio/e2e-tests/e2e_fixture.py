"""Seed an E2E database for a local server or a CI snapshot."""

import argparse
import tempfile
from collections.abc import Callable
from pathlib import Path

import duckdb

import lightly_studio as ls
from lightly_studio.database import db_manager


def run(seed: Callable[[], None], default_db_file: str | None = None) -> None:
    """Run the fixture and serve it, or write a new DuckDB snapshot and exit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-db", type=Path, help="Write the fixture to a new DuckDB file.")
    snapshot: Path | None = parser.parse_args().seed_db
    if snapshot is None:
        db_manager.connect(db_file=default_db_file, cleanup_existing=True)
        seed()
        ls.start_gui(open_browser=False)
        return

    if snapshot.exists():
        parser.error(f"Snapshot already exists: {snapshot}")
    with tempfile.TemporaryDirectory(dir=snapshot.parent) as directory:
        staged = Path(directory) / snapshot.name
        db_manager.connect(db_file=str(staged))
        try:
            seed()
        finally:
            db_manager.close()
        with duckdb.connect(str(staged), read_only=True) as database:
            if not database.execute("SELECT 1 FROM sample LIMIT 1").fetchone():
                raise ValueError("The E2E snapshot has no samples.")
        snapshot.hardlink_to(staged)
