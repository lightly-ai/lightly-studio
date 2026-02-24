
from __future__ import annotations


import lightly_studio as ls
from lightly_studio import db_manager

DB_FILE = "lexica_benchmark_x10.db"

db_manager.connect(cleanup_existing=False, db_file=DB_FILE)
dataset = ls.ImageDataset.load(name="default")
ls.start_gui()

    