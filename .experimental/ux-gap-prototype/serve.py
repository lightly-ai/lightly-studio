"""Start the LightlyStudio GUI on an existing DuckDB file."""

from __future__ import annotations

import argparse

import lightly_studio as ls
from lightly_studio.database import db_manager

parser = argparse.ArgumentParser()
parser.add_argument("--db", type=str, required=True)
parser.add_argument("--port", type=int, default=8001)
args = parser.parse_args()

db_manager.connect(db_file=args.db, must_exist=True)
ls.start_gui(port=args.port)
