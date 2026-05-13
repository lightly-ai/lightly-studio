# Reuse Datasets and Databases

LightlyStudio persists every dataset (metadata, tags, annotations, captions, and embeddings) into a DuckDB file named `lightly_studio.db`. By reopening the same database you can resume work without re-indexing images or recomputing embeddings.

## Choose where the database is stored

To store the DuckDB file elsewhere (for example, on a larger external disk or to maintain isolated projects), configure the database manager before creating or loading any datasets:

```python
from lightly_studio import db_manager

db_manager.connect(db_file="~/lightly_data/my-db-path.db")
```

!!! note
    Within the `.db` file all paths are stored as absolute paths. This allows the software to fetch data for visualization even if you move the `.db` file around.

## Reuse a dataset across runs

Restarting the same Python script will reopen the GUI with the previous state as long as you call `ImageDataset.load` or `ImageDataset.load_or_create` with the same name.

```python title="reuse_dataset.py"
from __future__ import annotations

import lightly_studio as ls

DATASET_NAME = "sport_shooting"
IMAGE_DIRS = ["data/primary_images", "data/new_images_later"]

# Everything persists inside lightly_studio.db automatically.
dataset = ls.ImageDataset.load_or_create(name=DATASET_NAME)

# Only new samples are added by `add_images_from_path`
for image_dir in IMAGE_DIRS:
    dataset.add_images_from_path(path=image_dir)

ls.start_gui()
```

- When you rerun the script later, only new files are indexed. Existing embeddings and annotations remain untouched; embeddings are generated only for the new samples (set `embed=False` to skip).
- Manual labels created in the GUI, metadata changed via Python, and tags assigned anywhere are all stored in `lightly_studio.db`, so you can stop/start the process at will.
- External files such as images/videos (`.jpg`, `.png`, `.mp4` files etc.) remain in their original location; keep them accessible so the GUI can display them when you reopen the dataset.

For dataset-type-specific loading examples, see [Image Dataset · From a Pre-Existing Dataset](image_dataset.md#from-a-pre-existing-dataset) and [Video Dataset · From a Pre-Existing Dataset](video_dataset.md#from-a-pre-existing-dataset).
