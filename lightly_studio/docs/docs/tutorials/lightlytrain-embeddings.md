# Explore LightlyTrain embeddings in LightlyStudio

In this tutorial, you learn how to train an embedding model with LightlyTrain, generate embeddings for your images, and explore and curate them in LightlyStudio.

You will:

- Train (or adapt) an embedding model on your own images with LightlyTrain.
- Export the model and run it inside LightlyStudio to embed your data.
- Explore the 2D embedding plot to find clusters, outliers, and near-duplicates.
- Select a diverse subset for labeling or training.

![LightlyTrain embeddings in LightlyStudio, colored by class — the clusters separate cleanly](https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/dinov2-embeddings.jpg){ width="100%" }

## Why train your own embedding model

Every embedding-based feature in LightlyStudio — the embedding plot, search, and sampling — is only as good as the model behind the vectors. A generic model like CLIP knows a little about everything. On specialized data, such as medical scans, satellite tiles, or factory-line images, it often smears distinct categories together, and the plot shows one undifferentiated blob.

A model trained on your own images pulls those categories apart. Clusters, outliers, and near-duplicates become visible, and every downstream selection gets sharper. LightlyTrain trains that model from your unlabeled images; LightlyStudio turns its embeddings into a map you can explore and curate.

The difference is easy to see. Below is the same dataset embedded two ways and colored by class — a generic model versus one adapted with LightlyTrain:

<div style="display: flex; flex-direction: column; gap: 1.5rem; margin: 1rem 0;">
  <figure style="margin: 0;">
    <img src="https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/mobile-clip-embeddings.jpg" alt="MobileCLIP embeddings colored by class" style="width: 100%; border-radius: 6px;">
    <figcaption><strong>A generic model (MobileCLIP).</strong> Classes overlap and bleed together.</figcaption>
  </figure>
  <figure style="margin: 0;">
    <img src="https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/dinov2-embeddings.jpg" alt="LightlyTrain embeddings colored by class" style="width: 100%; border-radius: 6px;">
    <figcaption><strong>Your LightlyTrain model.</strong> The same classes separate into distinct clusters.</figcaption>
  </figure>
</div>

## How the workflow fits together

LightlyTrain and LightlyStudio meet at one point: the embedding model.

1. **Train** an embedding model on your images with LightlyTrain.
2. **Export** it as a torch module.
3. **Load** the module into LightlyStudio, which runs it to embed your data.
4. **Explore and curate** the embeddings in the 2D plot.

This tutorial builds **two small scripts**: `train_and_export.py` (train the model — run it once) and `explore.py` (load the model into LightlyStudio and explore — run it any time). Splitting them means you train once, then reopen and explore without retraining. Runnable versions of both are on GitHub: [`example_lightlytrain_train_and_export.py`](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_lightlytrain_train_and_export.py) and [`example_lightlytrain_explore.py`](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_lightlytrain_explore.py).

## Prerequisites

To follow this tutorial, make sure you have:

- Python 3.10 or newer
- A GPU (recommended for training; the pretrained variant also runs on a CPU)
- About 2 GB of free disk space

## Installation

LightlyTrain and LightlyStudio are separate packages. Install both:

```bash
pip install lightly-train lightly-studio
```

## Step 1: Get a dataset

Create the first script, `train_and_export.py`, and download the example dataset. To use your own data instead, point `IMAGE_PATH` at a folder of images. (`explore.py` will start with these same two lines.)

```python title="train_and_export.py"
import lightly_studio as ls

dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")

IMAGE_PATH = f"{dataset_path}/coco_subset_128_images/images"
```

## Step 2: Train an embedding model

Distillation adapts a strong pretrained backbone to your own images, using no labels. `dinov2/vits14` starts from pretrained weights, so a single pass already gives usable embeddings; train longer to adapt the model more closely to your data.

```python title="train_and_export.py"
import lightly_train

lightly_train.pretrain(
    out="out/pretrain",
    data=IMAGE_PATH,
    model="dinov2/vits14",
    epochs=1,  # A quick pass. Raise it (e.g. 10 or more) to adapt further to your data.
    overwrite=True,  # Allow re-running over an existing output directory.
)
```

Training writes a checkpoint to `out/pretrain/checkpoints/last.ckpt`. Any name from `lightly_train.list_models()` works for `model`.

## Step 3: Export the embedding model

Export the trained model as a plain torch module. LightlyStudio loads this file and runs it directly.

```python title="train_and_export.py"
lightly_train.export(
    out="out/embedding_model.pt",
    checkpoint="out/pretrain/checkpoints/last.ckpt",
    part="embedding_model",
    format="torch_model",
    overwrite=True,
)
```

## Step 4: Load the model into LightlyStudio

Now create the second script, `explore.py`. It re-locates the images, loads the model you exported, and registers a generator that runs it — so LightlyStudio embeds each sample (whole images, object crops, and video frames) as you add it to a dataset.

!!! example "Beta API"
    The embeddings API is in beta. Its interface may change in future releases without a deprecation period.

Register the generator **before** you create the dataset, so ingestion embeds with it.

```python title="explore.py"
from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from torchvision import transforms

import lightly_studio as ls
from lightly_studio.dataset import file_utils, image_crop_embedding, image_embedding
from lightly_studio.dataset.embedding_result import EmbeddingResult
from lightly_studio.dataset.image_embedding import EmbeddingContext

dataset_path = ls.utils.download_example_dataset(download_dir="dataset_examples")
IMAGE_PATH = f"{dataset_path}/coco_subset_128_images/images"

IMAGE_SIZE = 224
# LightlyTrain normalizes with ImageNet statistics by default.
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class LightlyTrainEmbeddingGenerator(ls.ImageEmbeddingGenerator):
    """Run a model exported from LightlyTrain to embed images on the fly."""

    def __init__(self, model_file: str) -> None:
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # map_location="cpu" first, so a model exported on a GPU also loads on a CPU host.
        self._model = torch.load(
            model_file, map_location="cpu", weights_only=False
        ).to(self._device).eval()
        self._preprocess = transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ]
        )
        self._model_hash = file_utils.get_file_xxhash(Path(model_file))
        # EmbeddingModel.forward returns (B, D, 1, 1); infer D from a dummy pass.
        with torch.no_grad():
            dummy = torch.zeros(1, 3, IMAGE_SIZE, IMAGE_SIZE, device=self._device)
            self._dimension = int(self._model(dummy).flatten(1).shape[1])

    def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
        return ls.EmbeddingSpaceSpec(
            space_key=f"lightlytrain/{self._model_hash}", dimension=self._dimension
        )

    def embed_images(self, filepaths: list[str], show_progress: bool = True) -> EmbeddingResult:
        return image_embedding.embed_image_files_batched(
            filepaths=filepaths, context=self._context(), show_progress=show_progress
        )

    def embed_image_crops(
        self, image_crops: list[ls.ImageCrop], show_progress: bool = True
    ) -> EmbeddingResult:
        return image_crop_embedding.embed_image_crops_batched(
            image_crops=image_crops, context=self._context(), show_progress=show_progress
        )

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        return image_embedding.embed_pil_images_batched(
            images=images, context=self._context(), show_progress=show_progress
        )

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError("Vision-only model; text search is unavailable.")

    def _context(self) -> EmbeddingContext:
        return EmbeddingContext(
            embedding_dimension=self._dimension,
            max_batch_size=128,
            device=self._device,
            preprocess=self._preprocess,
            encode_batch=lambda batch: self._model(batch).flatten(1).cpu().numpy(),
        )


ls.db_manager.connect(cleanup_existing=True)
ls.set_default_embedding_model(LightlyTrainEmbeddingGenerator("out/embedding_model.pt"))

dataset = ls.ImageDataset.create(name="lightlytrain-embeddings")
dataset.add_images_from_path(path=IMAGE_PATH)
```

!!! note "Match your training normalization"
    The transform above matches LightlyTrain's ImageNet default. If you trained with custom `normalize_args`, pass the same mean and std.

!!! warning "Keep the same LightlyTrain version"
    `torch.load(..., weights_only=False)` unpickles LightlyTrain's model class, so the environment that runs LightlyStudio needs the same `lightly-train` version you exported with.

Text search stays off, because the model has no text encoder. See [Embeddings](../concepts_and_tools/embeddings.md) for the full protocol.

!!! note "Alternative: precompute the embeddings"
    Prefer to embed once, offline? Run `lightly_train.embed(...)` to write vectors to a file, then load them with the pattern in [`example_load_existing_embeddings.py`](https://github.com/lightly-ai/lightly-studio/blob/main/lightly_studio/src/lightly_studio/examples/example_load_existing_embeddings.py). That path embeds whole images only.

## Step 5: Explore the embedding map

Add one line to the end of `explore.py` to open the app:

```python title="explore.py"
ls.start_gui(open_browser=True)
```

Now run both scripts — train once, then explore:

```bash
python train_and_export.py   # train and export the model (slow; run once)
python explore.py            # embed your data and open LightlyStudio
```

Click the `Embed` button in the top right to open the embedding plot. It shows every image as a point in a 2D projection (PaCMAP) of the embedding space.

![The embedding plot after loading LightlyTrain embeddings, colored by class](https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/dinov2-embeddings.jpg){ width="100%" }

Read the map:

- **Hover a point** to preview its image.
- **Look for clusters** — tight groups are visually similar images; a well-trained model separates your categories into distinct blobs.
- **Watch the edges** — points far from any cluster are outliers or mislabeled data worth a look.
- **Spot near-duplicates** — points stacked on top of each other are almost identical images.

!!! tip
    The embedding plot renders best in Firefox.

### What a cluster contains

Lasso a tight cluster to scope the grid to its images, and they turn out to be one coherent group. The embedding even splits a single class into finer sub-groups — here, anglers holding a tench versus the fish on its own:

<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin: 1rem 0;">
  <figure style="margin: 0;">
    <img src="https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/cluster-cassette.jpg" alt="A lassoed cluster of cassette players" style="width: 100%; border-radius: 6px;">
    <figcaption>Cassette players.</figcaption>
  </figure>
  <figure style="margin: 0;">
    <img src="https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/cluster-parachute.jpg" alt="A lassoed cluster of parachutes" style="width: 100%; border-radius: 6px;">
    <figcaption>Parachutes.</figcaption>
  </figure>
  <figure style="margin: 0;">
    <img src="https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/cluster-tench.jpg" alt="A lassoed cluster of anglers holding a tench" style="width: 100%; border-radius: 6px;">
    <figcaption>Anglers holding a tench.</figcaption>
  </figure>
  <figure style="margin: 0;">
    <img src="https://storage.googleapis.com/lightly-public/studio/tutorials/lightlytrain-embeddings/cluster-fish.jpg" alt="A lassoed cluster of tench on their own" style="width: 100%; border-radius: 6px;">
    <figcaption>Tench on their own.</figcaption>
  </figure>
</div>

## Step 6: Select and curate a subset

The map is not just for looking. Turn what you see into a curated subset. A diversity selection picks a spread of samples across the whole embedding space, so a smaller labeling or training set still covers the variety in your data. Add it to `explore.py` **just before** the `ls.start_gui(...)` line:

```python title="explore.py"
dataset.query().sampling().diverse(
    n_samples_to_select=32, sampling_result_tag_name="diverse_subset"
)
```

The result is saved as a tag. Open it in the grid to review the picks, or color the embedding plot by the tag to see the spread. You can do the same by hand: lasso a region in the plot to scope the grid to those samples, inspect them, and tag what you want to keep. Selecting points and inspecting samples works in both directions. For every strategy — diverse, deduplication, similarity, and typicality — see [Sampling](../concepts_and_tools/sampling.md).

## Conclusion

In this tutorial, you trained an embedding model on your own images with LightlyTrain, exported it, and ran it inside LightlyStudio to explore and curate your data.

The connection between the two products is a single model file. Once LightlyStudio runs it, the embedding plot and every sampling strategy work just as they do with a built-in model — but now the space reflects a model that understands your data. Text search is the one exception: this model is vision-only.

To go further, train on your full dataset with more epochs, try a different backbone from `lightly_train.list_models()`, or read [Embeddings](../concepts_and_tools/embeddings.md) and [Sampling](../concepts_and_tools/sampling.md) to get more out of the map.
