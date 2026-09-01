# Explore LightlyTrain embeddings in LightlyStudio

In this tutorial, you learn how to train an embedding model with LightlyTrain, generate embeddings for your images, and explore and curate them in LightlyStudio.

You will:

- Train (distill) an embedding model on your own images with LightlyTrain.
- Generate embeddings for those images with the trained model.
- Load the embeddings into LightlyStudio through a small generator.
- Explore the 2D embedding plot to find clusters, outliers, and near-duplicates.
- Select a diverse subset for labeling or training.

![The embedding plot in LightlyStudio, colored by cluster](https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/embedding-plot.jpg){ width="100%" }

## Why train your own embedding model

Every embedding-based feature in LightlyStudio — the embedding plot, search, and sampling — is only as good as the model behind the vectors. A generic model like CLIP knows a little about everything. On specialized data, such as medical scans, satellite tiles, or factory-line images, it often smears distinct categories together, and the plot shows one undifferentiated blob.

A model trained on your own images pulls those categories apart. Clusters, outliers, and near-duplicates become visible, and every downstream selection gets sharper. LightlyTrain trains that model from your unlabeled images; LightlyStudio turns its embeddings into a map you can explore and curate.

## How the workflow fits together

LightlyTrain and LightlyStudio meet at one point: the embeddings.

1. **Train** an embedding model on your images with LightlyTrain.
2. **Generate** embeddings for the same images with the trained model.
3. **Load** those embeddings into LightlyStudio.
4. **Explore and curate** them in the embedding plot.

This tutorial builds a single script, `train_and_explore.py`, one step at a time. The full script is also available as [`example_lightlytrain_embeddings.py`](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_lightlytrain_embeddings.py).

## Prerequisites

To follow this tutorial, make sure you have:

- Python 3.10 or newer
- A GPU (recommended for training; the low-epoch run also works on a CPU)
- About 2 GB of free disk space

## Installation

LightlyTrain and LightlyStudio are separate packages. Install both:

```bash
pip install lightly-train lightly-studio
```

## Step 1: Get a dataset

Create a script, `train_and_explore.py`, and download the example dataset. To use your own data instead, point `IMAGE_PATH` at a folder of images.

```python title="train_and_explore.py"
import lightly_studio as ls

dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

IMAGE_PATH = f"{dataset_path}/coco_subset_128_images/images"
```

## Step 2: Train an embedding model

Distillation teaches a compact model to reproduce the features of a strong pretrained backbone, using only your unlabeled images. Add the snippet below to train `dinov2/vits14` on the dataset.

```python title="train_and_explore.py"
import lightly_train

lightly_train.pretrain(
    out="out/pretrain",
    data=IMAGE_PATH,
    model="dinov2/vits14",
    epochs=10,
)
```

Training writes a checkpoint to `out/pretrain/checkpoints/last.ckpt`. Any name from `lightly_train.list_models()` works for `model`.

!!! tip "Use a pretrained backbone for a quick run"
    `dinov2/vits14` starts from pretrained weights, so even a short run gives you a working embedding model. To skip the GPU, lower `epochs` (for example `epochs=1`) — enough to produce the checkpoint that Step 3 needs. Raise it later when you train on your real data.

## Step 3: Generate embeddings

With the model trained, embed every image. `lightly_train.embed` runs the model over the folder and writes the vectors to a file.

```python title="train_and_explore.py"
lightly_train.embed(
    out="out/embeddings.pt",
    data=IMAGE_PATH,
    checkpoint="out/pretrain/checkpoints/last.ckpt",
    format="torch",
)
```

The output is a dictionary, `{"filenames": [...], "embeddings": tensor}`, with one row per image. These are the vectors LightlyStudio will visualize.

## Step 4: Load the embeddings into LightlyStudio

LightlyStudio computes embeddings itself when you add data. To make it reuse the vectors from Step 3 instead, register a generator that looks each one up by file path.

!!! example "Beta API"
    The embeddings API is in beta. Its interface may change in future releases without a deprecation period.

Add the generator and load the dataset. Register the generator **before** you create the dataset, so ingestion uses your vectors.

```python title="train_and_explore.py"
from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image

from lightly_studio.dataset import file_utils
from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.models.embedding_model import EmbeddingSpaceDescription


class LightlyTrainEmbeddingsGenerator(ls.ImageEmbeddingGenerator):
    """Serve embeddings precomputed by lightly_train.embed, keyed by file path."""

    def __init__(self, embeddings_file: str, data_dir: str) -> None:
        blob = torch.load(embeddings_file, weights_only=True)
        vectors: NDArray[np.float32] = blob["embeddings"].to(torch.float32).numpy()
        self._embedding_dimension = int(vectors.shape[1])
        # embed() filenames are relative to data_dir; LightlyStudio stores absolute paths.
        self._by_path = {
            (Path(data_dir) / name).absolute().as_posix(): vectors[index]
            for index, name in enumerate(blob["filenames"])
        }
        self._model_hash = file_utils.get_file_xxhash(Path(embeddings_file))

    def get_embedding_model_input(self) -> EmbeddingSpaceDescription:
        return EmbeddingSpaceDescription(
            name="LightlyTrain",
            embedding_model_hash=self._model_hash,
            embedding_dimension=self._embedding_dimension,
        )

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        rows: list[NDArray[np.float32]] = []
        kept_indices: list[int] = []
        for index, filepath in enumerate(filepaths):
            vector = self._by_path.get(filepath)
            if vector is None:
                continue
            rows.append(vector)
            kept_indices.append(index)
        embeddings = (
            np.stack(rows)
            if rows
            else np.empty((0, self._embedding_dimension), dtype=np.float32)
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError("Vision-only model; text search is unavailable.")

    def embed_image_crops(
        self, image_crops: list[ls.ImageCrop], show_progress: bool = True
    ) -> EmbeddingResult:
        raise NotImplementedError("Precomputed whole-image vectors only.")

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        raise NotImplementedError("Precomputed vectors are keyed by file path.")


ls.db_manager.connect(cleanup_existing=True)
ls.set_default_embedding_model(
    LightlyTrainEmbeddingsGenerator(embeddings_file="out/embeddings.pt", data_dir=IMAGE_PATH)
)

dataset = ls.ImageDataset.create(name="lightlytrain-embeddings")
dataset.add_images_from_path(path=IMAGE_PATH)
```

The generator serves whole-image vectors; the other methods raise, so text search and object-level embeddings stay off for this model. See [Embeddings](../concepts_and_tools/embeddings.md) for the full protocol.

!!! note "Advanced: embed live inside LightlyStudio"
    Instead of precomputing, you can run the exported model inside LightlyStudio and embed images on the fly — this also covers object crops. See [`example_custom_embedding_model.py`](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_custom_embedding_model.py) for the pattern.

## Step 5: Explore the embedding map

Run the script. It trains the model, generates the embeddings, and loads them into a dataset.

```bash
python train_and_explore.py
```

Then open LightlyStudio and click the `Embed` button in the top right to open the embedding plot. It shows every image as a point in a 2D projection (PaCMAP) of the embedding space.

![The embedding plot after loading LightlyTrain embeddings](https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/embedding-plot-explore.jpg){ width="100%" }

Read the map:

- **Hover a point** to preview its image.
- **Look for clusters** — tight groups are visually similar images; a well-trained model separates your categories into distinct blobs.
- **Watch the edges** — points far from any cluster are outliers or mislabeled data worth a look.
- **Spot near-duplicates** — points stacked on top of each other are almost identical images.

!!! tip
    The embedding plot renders best in Firefox.

## Step 6: Select and curate a subset

The map is not just for looking. Turn what you see into a curated subset. A diversity selection picks a spread of samples across the whole embedding space, so a smaller labeling or training set still covers the variety in your data.

```python title="train_and_explore.py"
dataset.query().sampling().diverse(
    n_samples_to_select=32, sampling_result_tag_name="diverse_subset"
)
```

The result is saved as a tag. Open it in the grid to review the picks, or color the embedding plot by the tag to see the spread. You can do the same by hand: lasso a region in the plot to scope the grid to those samples, inspect them, and tag what you want to keep. Selecting points and inspecting samples works in both directions. For every strategy — diverse, deduplication, similarity, and typicality — see [Sampling](../concepts_and_tools/sampling.md).

```python title="train_and_explore.py"
ls.start_gui(open_browser=True)
```

## Conclusion

In this tutorial, you trained an embedding model on your own images with LightlyTrain, generated embeddings, and loaded them into LightlyStudio to explore and curate.

The connection between the two products is a single file of vectors. Once they are in LightlyStudio, the embedding plot, search, and every sampling strategy work the same as with a built-in model — but now the space reflects a model that understands your data.

To go further, train on your full dataset with more epochs, try a different backbone from `lightly_train.list_models()`, or read [Embeddings](../concepts_and_tools/embeddings.md) and [Sampling](../concepts_and_tools/sampling.md) to get more out of the map.
