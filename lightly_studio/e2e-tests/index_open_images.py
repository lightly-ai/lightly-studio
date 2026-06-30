"""Load the public Open Images `test/` split (~125,436 images) and launch the UI.

Streams directly from the public CVDF S3 mirror — no local download.
Modeled on e2e-tests/index_datasets.py.

Bucket: s3://open-images-dataset/  (public / anonymous access)
  test/        125,436 images   <- used here
  validation/   41,620 images
  train/     1,743,042 images

Run:
    pip install "lightly-studio[cloud-storage]"
    python index_open_images.py
"""

import os

import fsspec

# Open Images object names are 16-char lowercase-hex IDs, so fan the listing out
# across 256 two-character hex prefixes (set before the lister reads these).
os.environ.setdefault("LIGHTLY_STUDIO_LIST_PREFIXES", "0123456789abcdef")
os.environ.setdefault("LIGHTLY_STUDIO_LIST_PREFIX_DEPTH", "2")

import lightly_studio as ls
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.database import db_manager

# Configure the shared S3 filesystem for this run.
#   anon                 -> open-images-dataset is public (--no-sign-request).
#   config_kwargs        -> botocore caps the connection pool at 10 by default,
#                           which throttles concurrent reads no matter how many
#                           worker threads we use. Raise it so the loader's
#                           thread pool actually runs in parallel.
#   default_block_size   -> we only need the image header for width/height; a
#                           small read-ahead avoids pulling multi-MB blocks per
#                           image.
# These defaults are applied to every `fsspec.filesystem("s3")` / `fsspec.open`
# in this process (listing + dimension reads).
fsspec.config.conf["s3"] = {
    "anon": True,
    "default_block_size": 64 * 1024,
    "config_kwargs": {"max_pool_connections": 256},
}

# Connect to the database
db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)

# Create dataset by streaming images straight from S3 (no download).
#   embed=False            -> skip embedding computation (would read every image).
#   read_dimensions=False  -> skip the per-image header read for width/height too,
#                             so indexing is just listing + DB inserts (seconds, not
#                             hours). The S3 path (incl. the Open Images ID) is stored,
#                             so dimensions/embeddings can be backfilled later.
#   list_workers=256       -> discover files concurrently by fanning the listing out
#                             across name prefixes instead of paginating serially;
#                             matches the 256 two-character hex prefixes so they all
#                             list at once.
dataset = ImageDataset.create(name="open_images_test")
dataset.add_images_from_path(
    path="s3://open-images-dataset/test/",
    embed=False,
    read_dimensions=False,
    list_workers=256,
)

ls.start_gui()
