# Sampling

Sampling helps you select representative subsets from your dataset. LightlyStudio provides sampling strategies that leverage embeddings to pick diverse, balanced, or otherwise optimized subsets for labeling, training, or review. Use the GUI for quick, one-off sampling. Use the Python API when you need reusable, configurable, or combined sampling strategies in code.

## Prerequisites

Sampling is a premium feature and requires a valid LightlyStudio license key. Set the `LIGHTLY_STUDIO_LICENSE_KEY` environment variable before using sampling features:

=== "Linux/macOS"

    ```bash
    export LIGHTLY_STUDIO_LICENSE_KEY="license_key_here"
    ```

=== "Windows"

    ```powershell
    $env:LIGHTLY_STUDIO_LICENSE_KEY="license_key_here"
    ```

## Sampling in GUI

Open the dialog from the `Menu` button in the top-right corner and select `Selection`. The dialog shows a dropdown with available sampling strategies. Specify the number of samples and the tag name that should be used. [Sampling in Python](#sampling-in-python) supports more sampling strategies than available in the GUI and also lets you learn more about how they work.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/sampling_workflow.mp4" type="video/mp4">
</video>

## Sampling in Python

Each strategy is configured directly from a [`DatasetQuery`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery) via [`selection()`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery.selection). The sampled items are stored under the tag passed as `selection_result_tag_name`, so you can filter or export them later. `selection_result_tag_name` must be a tag name that does not yet exist in the dataset.

### Filtering before sampling

By default, sampling considers all samples in the dataset. You can narrow the candidate set first with `match()`, and the selection will only consider the matching samples:

```py
import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField

dataset = ls.ImageDataset.load_or_create()

# Sample 10 diverse items from images with width >= 1920 only.
dataset.match(ImageSampleField.width >= 1920).selection().diverse(
    n_samples_to_select=10,
    selection_result_tag_name="diverse_hd",
)
```

See [Search and Filter](search_and_filter.md#query-in-python) for more filtering options.

### Sampling Strategies

#### Diverse

Diversity sampling picks samples that cover the dataset as broadly as possible based on embeddings, maximizing the spread across embedding space.

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path="/path/to/image_dataset")

# Sample a diverse subset of 10 samples.
dataset.query().selection().diverse(
    n_samples_to_select=10,
    selection_result_tag_name="diverse_selection",
)
```

If your dataset has multiple embedding models, pass `embedding_model_name` to specify which one to use. See [`Selection.diverse`](../api/selection.md#lightly_studio.selection.select.Selection.diverse) for the full API reference.

#### Metadata Weighting

Metadata weighting selects samples by treating a numeric metadata field as a score: samples with higher values are preferred. Any float or int metadata field can be used as the weight.

```py
import lightly_studio as ls

dataset = ls.ImageDataset.load_or_create()

# Sample the 5 items with the highest value of a custom "sharpness" metadata field.
dataset.query().selection().metadata_weighting(
    n_samples_to_select=5,
    selection_result_tag_name="sharpest_samples",
    metadata_key="sharpness",
)

# Sample the 5 items with the lowest value of a custom "sharpness" metadata field.
dataset.query().selection().metadata_weighting(
    n_samples_to_select=5,
    selection_result_tag_name="blurriest_samples",
    metadata_key="sharpness",
    strength=-1
)
```

See [`Selection.metadata_weighting`](../api/selection.md#lightly_studio.selection.select.Selection.metadata_weighting) for the full API reference.

#### Typicality Sampling and Outlier Sampling

Typicality is a per-sample score derived from embeddings. Samples that are close to many other samples in embedding space (i.e. "typical" of the dataset) receive a high score; outliers receive a low score. It is computed with `compute_typicality_metadata` and then passed to `metadata_weighting`.

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path="/path/to/image_dataset")

# Compute and store typicality scores as metadata.
dataset.compute_typicality_metadata(metadata_name="typicality")

# Sample the 5 most typical items.
dataset.query().selection().metadata_weighting(
    n_samples_to_select=5,
    selection_result_tag_name="typical_selection",
    metadata_key="typicality",
)

# Sample 5 outliers.
dataset.query().selection().metadata_weighting(
    n_samples_to_select=5,
    selection_result_tag_name="outlier_selection",
    metadata_key="typicality",
    strength=-1
)
```

If your dataset has multiple embedding models, pass `embedding_model_name` to select which one to use. See [`Dataset.compute_typicality_metadata`](../api/dataset.md#lightly_studio.core.dataset.Dataset.compute_typicality_metadata) for the full API reference.

#### Similarity

Similarity-based sampling selects samples based on their embedding similarity to a reference set. First, tag the samples you want to use as the query, then compute per-sample similarity scores with `compute_similarity_metadata`, and finally pass those scores to `metadata_weighting`.

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path="/path/to/image_dataset")

# Define a query set by tagging some samples.
dataset[:5].add_tag("my_query_samples")

# Compute similarity to the tagged samples and store it as metadata.
# The method returns the name under which the metadata was stored.
metadata_name = dataset.compute_similarity_metadata(
    query_tag_name="my_query_samples",
    metadata_name="similarity_to_query", # optional. auto-generated when omitted.
)

# Sample the 10 items most similar to the query set.
dataset.query().selection().metadata_weighting(
    n_samples_to_select=10,
    selection_result_tag_name="similar_to_query_selection",
    metadata_key=metadata_name,
)
```

`metadata_name` is optional. When omitted, a unique name is generated automatically and returned. See [`Dataset.compute_similarity_metadata`](../api/dataset.md#lightly_studio.core.dataset.Dataset.compute_similarity_metadata) for the full API reference.

#### Class Balancing

Class balancing selects samples based on the distribution of annotation classes. This is useful for fixing class imbalance. For example, ensuring you have enough "pedestrians" in a driving dataset.

!!! note "Annotations required"
    This strategy requires the dataset to have [annotations](annotations.md). It is primarily designed for **object detection** annotations. Segmentation masks may produce unexpected results, as mask definitions can vary (e.g., all pixels of a class in a single mask vs. multiple masks per class).

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()

# Option 1: Balance classes uniformly (e.g. equal number of cats and dogs)
dataset.query().selection().annotation_balancing(
    n_samples_to_select=50,
    selection_result_tag_name="balanced_uniform",
    target_distribution="uniform",
)

# Option 2: Mirror the class distribution of the input set
dataset.query().selection().annotation_balancing(
    n_samples_to_select=50,
    selection_result_tag_name="balanced_input",
    target_distribution="input",
)

# Option 3: Define a specific target distribution (e.g. 20% cat, 80% dog)
dataset.query().selection().annotation_balancing(
    n_samples_to_select=50,
    selection_result_tag_name="balanced_custom",
    target_distribution={"cat": 0.2, "dog": 0.8},
)
```

The three `target_distribution` options are:

| Value | Behavior |
|---|---|
| `"uniform"` | Equal share for every class present in the dataset |
| `"input"` | Mirrors the class distribution of the candidate input set |
| `{class: ratio, ...}` | Explicit target ratios; must sum to 1.0 |

#### Multiple Strategies

You can combine several strategies into a single sampling run. All configured strategies are evaluated together and weighted by the `strength` parameter.

```py
import lightly_studio as ls
from lightly_studio.selection.selection_config import (
    MetadataWeightingStrategy,
    EmbeddingDiversityStrategy,
)

# Load your dataset
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path="/path/to/image_dataset")

# Compute typicality and store it as `typicality` metadata
dataset.compute_typicality_metadata(metadata_name="typicality")

# Sample 10 items by combining typicality and diversity,
# with diversity weighted twice as strongly.
dataset.query().selection().multi_strategies(
    n_samples_to_select=10,
    selection_result_tag_name="multi_strategy_selection",
    selection_strategies=[
        MetadataWeightingStrategy(metadata_key="typicality", strength=1.0),
        EmbeddingDiversityStrategy(embedding_model_name="my_model_name", strength=2.0),
    ],
)
```

### Exporting Sampled Items

Every sampling run writes its result to the tag passed as `selection_result_tag_name`. You can export those samples from the GUI, or query them in Python by matching on the tag.

```py
import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField

dataset = ls.ImageDataset.load("my-dataset")

sampled_items = (
    dataset.match(ImageSampleField.tags.contains("diverse_selection")).to_list()
)

with open("export.txt", "w") as f:
    for sample in sampled_items:
        f.write(f"{sample.file_path_abs}\n")
```

For more details on filtering by tag or exporting subsets, see [Search and Filter](search_and_filter.md#query-in-python) and [Export](export.md).
