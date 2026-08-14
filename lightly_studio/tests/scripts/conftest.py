import sys
from pathlib import Path

# The scripts import each other by bare module name (e.g. ``import run_egocentric_qa``),
# which resolves at runtime because the script's own directory is on ``sys.path``. Put the
# scripts directory on the path here so the same imports resolve under pytest.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
