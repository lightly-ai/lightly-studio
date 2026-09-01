"""Train and export an embedding model with LightlyTrain.

Part 1 of a two-script example. This trains (or briefly adapts) a model on your
images and exports it as a torch module to ``out/embedding_model.pt``. Then run
``example_lightlytrain_explore.py`` to load it into LightlyStudio.

LightlyTrain is a separate install and needs Python 3.10 or newer:

    pip install lightly-train lightly-studio

``EPOCHS = 1`` is a quick pass that already gives usable embeddings; raise it
(for example to 10) to adapt the model more closely to your own images.
"""

from __future__ import annotations

from pathlib import Path

import lightly_train  # type: ignore[import-not-found]

import lightly_studio as ls

# Backbone to train/adapt. Any name from lightly_train.list_models() works.
MODEL = "dinov2/vits14"
# A quick pass that already gives usable embeddings. Raise it (e.g. 10) to adapt further.
EPOCHS = 1
PRETRAIN_DIR = "out/pretrain"
MODEL_FILE = "out/embedding_model.pt"

# 1. Get a dataset. Swap in your own image folder here.
data_dir = ls.utils.download_example_dataset(download_dir="dataset_examples")
images_path = str(Path(data_dir) / "coco_subset_128_images" / "images")

# 2. Train (or briefly adapt) an embedding model on the images.
# overwrite=True lets you re-run this script over an existing output directory.
lightly_train.pretrain(
    out=PRETRAIN_DIR, data=images_path, model=MODEL, epochs=EPOCHS, overwrite=True
)

# 3. Export the trained embedding model as a torch module Studio can run.
lightly_train.export(
    out=MODEL_FILE,
    checkpoint=f"{PRETRAIN_DIR}/checkpoints/last.ckpt",
    part="embedding_model",
    format="torch_model",
    overwrite=True,
)
