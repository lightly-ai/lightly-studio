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

import tarfile
import urllib.request
from pathlib import Path

import lightly_train  # type: ignore[import-not-found]

# Backbone to train/adapt. Any name from lightly_train.list_models() works.
MODEL = "dinov2/vits14"
# A quick pass that already gives usable embeddings. Raise it (e.g. 10) to adapt further.
EPOCHS = 1
PRETRAIN_DIR = "out/pretrain"
MODEL_FILE = "out/embedding_model.pt"

# 1. Download Imagenette (a 10-class ImageNet subset), one folder per class.
archive = Path("imagenette2-320.tgz")
if not archive.exists():
    urllib.request.urlretrieve(
        "https://s3.amazonaws.com/fast-ai-imageclas/imagenette2-320.tgz", archive
    )
    with tarfile.open(archive) as tar:
        tar.extractall(".")
images_path = "imagenette2-320/val"

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
