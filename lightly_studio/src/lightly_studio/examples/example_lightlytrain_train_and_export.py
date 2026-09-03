"""Distill a large embedding model into a small one with LightlyTrain.

Part 1 of a two-script example. This distills a ``dinov3/vitb16`` teacher into a
``dinov3/vitt16`` student on unlabeled images, and exports the student to
``out/embedding_model.pt``. Then run ``example_lightlytrain_explore.py`` to load
the student into LightlyStudio.

The student is 5.5M parameters against the teacher's 85.7M, so it is much cheaper
to run for every image you embed.

LightlyTrain is a separate install and needs Python 3.10 or newer:

    pip install lightly-train lightly-studio

``EPOCHS = 100`` takes about 21 minutes on 2 NVIDIA RTX 4090 GPUs.

Distillation only helps when a larger model beats a smaller one on your data. On
CUB-200 that margin is large, because species recognition is fine-grained. On
coarse data, where a small model already scores close to a large one, there is
nothing for the student to gain.
"""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

import lightly_train  # type: ignore[import-not-found]

# The student. This is the model that LightlyStudio runs later.
MODEL = "dinov3/vitt16"
# The teacher. Larger and stronger; used only during distillation.
TEACHER = "dinov3/vitb16"
EPOCHS = 100
PRETRAIN_DIR = "out/pretrain"
MODEL_FILE = "out/embedding_model.pt"

# 1. Download CUB-200-2011 (11,788 images of 200 bird species), one folder per species.
archive = Path("CUB_200_2011.tgz")
if not archive.exists():
    urllib.request.urlretrieve(
        "https://data.caltech.edu/records/65de6-vp158/files/CUB_200_2011.tgz", archive
    )
    with tarfile.open(archive) as tar:
        # filter="data" refuses members that would write outside the target directory.
        # It is the default from Python 3.14 and is available in Python 3.12, and in
        # recent 3.10 and 3.11 patch releases.
        tar.extractall(".", filter="data")
IMAGE_PATH = "CUB_200_2011/images"

# 2. Distill the teacher into the student. This uses no labels.
# overwrite=True lets you re-run this script over an existing output directory.
lightly_train.pretrain(
    out=PRETRAIN_DIR,
    data=IMAGE_PATH,
    model=MODEL,
    method="distillation",
    method_args={"teacher": TEACHER},
    epochs=EPOCHS,
    overwrite=True,
)

# 3. Export the student as a torch module that LightlyStudio can run.
lightly_train.export(
    out=MODEL_FILE,
    checkpoint=f"{PRETRAIN_DIR}/checkpoints/last.ckpt",
    part="embedding_model",
    format="torch_model",
    overwrite=True,
)
