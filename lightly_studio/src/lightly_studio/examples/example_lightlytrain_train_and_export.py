"""Distill a large embedding model into a small one with LightlyTrain.

Part 1 of a two-script example. This distills a ``dinov3/vitb16`` teacher into a
``dinov3/vitt16`` student on unlabeled images, and exports the student to
``out/embedding_model.pt``. Then run ``example_lightlytrain_explore.py`` to load
the student into LightlyStudio.

The student is 5.5M parameters against the teacher's 85.7M, so it is much cheaper
to run for every image you embed.

LightlyTrain is a separate install. This script needs Python 3.10.12+, 3.11.4+,
or 3.12+, because it passes ``filter`` to ``tarfile.extractall``:

    pip install lightly-train lightly-studio

``EPOCHS = 100`` takes about 21 minutes on 2 NVIDIA RTX 4090 GPUs.

Distillation only helps when a larger model beats a smaller one on your data. On
CUB-200 that margin is large, because species recognition is fine-grained. On
coarse data, where a small model already scores close to a large one, there is
nothing for the student to gain.
"""

from __future__ import annotations

import tarfile
from pathlib import Path

import lightly_train  # type: ignore[import-not-found]

from lightly_studio.dataset import file_utils

# The student. This is the model that LightlyStudio runs later.
MODEL = "dinov3/vitt16"
# The teacher. Larger and stronger; used only during distillation.
TEACHER = "dinov3/vitb16"
EPOCHS = 100
PRETRAIN_DIR = "out/pretrain"
MODEL_FILE = "out/embedding_model.pt"
CUB_URL = "https://data.caltech.edu/records/65de6-vp158/files/CUB_200_2011.tgz"
ARCHIVE = Path("CUB_200_2011.tgz")
# The archive also holds a top-level attributes.txt, so extract into a directory of
# our own instead of the working directory.
DATA_DIR = Path("data")
# Touched only after extractall returns. CUB_200_2011/images appears three members
# into the archive, so its presence says nothing about whether extraction finished.
EXTRACT_DONE = DATA_DIR / ".extracted"
IMAGE_PATH = DATA_DIR / "CUB_200_2011" / "images"


def download_dataset() -> None:
    """Download CUB-200-2011 (11,788 images of 200 bird species), one folder per species.

    The helper downloads to a temp file and moves it into place only on success, so an
    interrupted download is never mistaken for a complete one.
    """
    file_utils.download_file_if_does_not_exist(url=CUB_URL, local_filename=ARCHIVE)
    if not EXTRACT_DONE.exists():
        with tarfile.open(ARCHIVE) as tar:
            # filter="data" refuses members that would write outside DATA_DIR.
            # It needs Python 3.10.12+, 3.11.4+, or 3.12+, and is the default from 3.14.
            tar.extractall(DATA_DIR, filter="data")
        EXTRACT_DONE.touch()


def distill() -> None:
    """Distill the teacher into the student. This uses no labels.

    resume_interrupted=True picks a crashed run back up where it stopped instead of
    repeating all 100 epochs. On a first run there is no checkpoint and it does nothing.
    """
    lightly_train.pretrain(
        out=PRETRAIN_DIR,
        data=IMAGE_PATH,
        model=MODEL,
        method="distillation",
        method_args={"teacher": TEACHER},
        epochs=EPOCHS,
        resume_interrupted=True,
    )


def export_student() -> None:
    """Export the student as a torch module that LightlyStudio can run."""
    lightly_train.export(
        out=MODEL_FILE,
        checkpoint=f"{PRETRAIN_DIR}/checkpoints/last.ckpt",
        part="embedding_model",
        format="torch_model",
        overwrite=True,
    )


# LightlyTrain spawns dataloader workers, which re-import this module on macOS and
# Windows. Without the guard, the calls below run again in every worker and the
# process dies during bootstrapping.
if __name__ == "__main__":
    download_dataset()
    distill()
    export_student()
