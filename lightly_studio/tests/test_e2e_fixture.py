"""Test publication of the E2E DuckDB snapshot."""

import subprocess
import sys
from pathlib import Path

E2E_TESTS_DIR = Path(__file__).resolve().parents[1] / "e2e-tests"


def test_run__failed_seed(tmp_path: Path) -> None:
    script = E2E_TESTS_DIR / "index_general.py"
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


def test_run__no_samples(tmp_path: Path) -> None:
    snapshot = tmp_path / "empty.db"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import e2e_fixture; e2e_fixture.run(seed=lambda: None)",
            "--seed-db",
            str(snapshot),
        ],
        cwd=E2E_TESTS_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "ValueError: The E2E snapshot has no samples." in result.stderr
    assert not snapshot.exists()
