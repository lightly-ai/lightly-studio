"""Test publication of the E2E DuckDB snapshot."""

import subprocess
import sys
from pathlib import Path


def test_failed_seed_leaves_no_snapshot(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "e2e-tests" / "index_general.py"
    snapshot = tmp_path / "general.db"
    # The empty working directory has no COCO fixture.
    result = subprocess.run(
        [sys.executable, str(script), "--seed-db", str(snapshot)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "instances_train2017.json" in result.stderr
    assert not snapshot.exists()
