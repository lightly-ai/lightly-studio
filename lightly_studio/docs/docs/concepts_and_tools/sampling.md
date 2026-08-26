---
title: Dataset Sampling Strategies Explained
description: Select diverse, balanced, or representative subsets from your dataset using LightlyStudio's embedding-based sampling strategies in the GUI or Python.
---

# Sampling

Sampling helps you select a smaller, more useful subset from a large dataset. Typical goals are
deciding what to label first, removing redundant data before training, or building a balanced review
set. LightlyStudio's strategies use embeddings (and, where relevant, your metadata or annotations) to
pick diverse, representative, or otherwise optimized subsets.

The rest of this page covers **which strategy to pick**, **what each one does**, and **how to run a
sampling** in the GUI or in Python.

## Choosing a strategy

Each strategy optimizes for a different goal. Start from what you are trying to achieve:

| I want to... | Use |
|---|---|
| Pick a diverse subset that covers the whole dataset | [Diverse](#diverse) |
| Keep a diverse subset that still reflects the real distribution | [Diverse + typicality](#typicality-and-outlier) |
| Find rare or unusual samples, such as edge cases, anomalies, or potentially mislabeled data | [Outliers](#typicality-and-outlier) |
| Clean up a dataset by removing near-duplicate images | [Deduplication](#deduplication) |
| Rank images by a number I have and keep the top ones (e.g. model confidence) | [Metadata weighting](#metadata-weighting) |
| Find more images based on failure cases | [Similarity](#similarity) |
| Balance how many objects of each class I have | [Class balancing](#class-balancing) |
| Balance the selection over a metadata field, e.g. equal amounts of every weather | [Metadata balancing](#metadata-balancing) |

You are not limited to one strategy. See
[Combining multiple strategies](#combining-multiple-strategies) to weight several in a single run.
For an end-to-end curation workflow that filters, deduplicates, and then samples a diverse training
set, see the [Curate a Traffic CCTV Dataset](../tutorials/yolo-traffic-cctv-object-detection.md)
tutorial.

## Sampling strategies

The examples below use the Python API. See [Running a sampling](#running-a-sampling) for the GUI, for
narrowing the candidate set first, and for exporting the result.

### Diverse

!!! tip "When to use"
    You have a large pool of unlabeled data and want the most informative subset to label first.
    This is especially useful when many samples look alike, for example video frames from the same
    scene: diverse sampling spreads the selection across embedding space so every labeling effort
    adds new information instead of more of the same.

Diversity sampling picks samples that cover the dataset as broadly as possible based on embeddings, maximizing the spread across embedding space. Because it favors spread, it tends to over-represent rare, sparse regions; if you want the selection to stay closer to the real distribution, combine it with [typicality](#typicality-and-outlier).

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path="/path/to/image_dataset")

# Sample a diverse subset of 10 samples.
dataset.query().sampling().diverse(
    n_samples_to_select=10,
    sampling_result_tag_name="diverse_sampling",
)
```

If your dataset has multiple embedding models, pass `embedding_model_name` to specify which one to use. See [`Sampling.diverse`](../api/sampling.md#lightly_studio.sampling.sample.Sampling.diverse) for the full API reference.

### Deduplication

!!! tip "When to use"
    You want to clean up a dataset, for example after merging several sources, after applying
    augmentations, or just to drop the last few percent of near-duplicates. Unlike
    [diverse](#diverse) sampling, which picks a fixed number of the most spread-out samples,
    deduplication keeps everything except samples that sit too close to one already kept, so you
    remove redundancy without deciding a target size up front.

Deduplication builds a subset in which no two selected samples are closer than `stopping_condition_minimum_distance` in embedding space. A sample is added to the result only if it is at least that far from every sample already selected; any sample that falls within the threshold is treated as a near-duplicate and skipped. Selection continues until `n_samples_to_select` samples have been collected or no sufficiently distinct sample remains, so fewer than `n_samples_to_select` samples may be returned.

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path="/path/to/image_dataset")

# Select up to 100 samples, stopping early once the remaining samples are
# closer than 0.1 to the already selected ones.
dataset.query().sampling().deduplicate(
    n_samples_to_select=100,
    sampling_result_tag_name="deduplicated_sampling",
    stopping_condition_minimum_distance=0.1,
)
```

The right value for `stopping_condition_minimum_distance` depends on the embedding model and the distances in your dataset. See [`Sampling.deduplicate`](../api/sampling.md#lightly_studio.sampling.sample.Sampling.deduplicate) for the full API reference.

### Metadata weighting

!!! tip "When to use"
    You already have a number attached to each sample that says how much you want it, and you want to
    sample by that number. A common case is active learning: keep the images your model is least
    confident about. See [Metadata](metadata.md) for how to attach or compute such fields.

Metadata weighting simply prefers samples with a higher (or, with a negative `strength`, lower) value of one numeric metadata field. It does not balance or spread the selection in any way. Any float or int metadata field can be used as the weight.

```py
import lightly_studio as ls

dataset = ls.ImageDataset.load_or_create()

# Sample the 5 items with the highest value of a custom "sharpness" metadata field.
dataset.query().sampling().metadata_weighting(
    n_samples_to_select=5,
    sampling_result_tag_name="sharpest_samples",
    metadata_key="sharpness",
)

# Sample the 5 items with the lowest value of a custom "sharpness" metadata field.
dataset.query().sampling().metadata_weighting(
    n_samples_to_select=5,
    sampling_result_tag_name="blurriest_samples",
    metadata_key="sharpness",
    strength=-1
)
```

See [`Sampling.metadata_weighting`](../api/sampling.md#lightly_studio.sampling.sample.Sampling.metadata_weighting) for the full API reference.

### Typicality and outlier

!!! tip "When to use"
    Two common cases. First, to keep a **diverse but representative** subset by combining typicality
    with [diversity](#diverse) (see the note below). Second, to surface **outliers**: the rare,
    unusual samples, which are useful for finding edge cases, anomalies, or mislabeled data. Outliers
    are not a separate strategy; you get them by weighting the typicality score with a negative
    `strength`, so low-typicality (rare) samples are preferred (see the example below).

Typicality is a per-sample score derived from embeddings. Samples that are close to many other samples in embedding space (i.e. "typical" of the dataset) receive a high score; outliers receive a low score. It is computed with `compute_typicality_metadata` and then passed to `metadata_weighting`.

!!! note "Diversity + typicality"
    On its own, diversity favors spread, so it can pull the selection toward an even mix of clusters
    even when the dataset is not evenly distributed. Adding typicality keeps dense regions weighted
    by how populated they are, so the selection stays diverse while still reflecting the real
    distribution. If your data is mostly cats with a few dogs, diversity alone could push you toward
    a roughly even cat/dog split, whereas diversity plus typicality keeps cats in the majority. It
    also means a large cluster (say 100 near-identical dogs of one breed) still contributes several
    samples rather than collapsing to one. Combine the two with
    [multiple strategies](#combining-multiple-strategies).

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()
dataset.add_images_from_path(path="/path/to/image_dataset")

# Compute and store typicality scores as metadata.
dataset.compute_typicality_metadata(metadata_name="typicality")

# Sample the 5 most typical items.
dataset.query().sampling().metadata_weighting(
    n_samples_to_select=5,
    sampling_result_tag_name="typical_sampling",
    metadata_key="typicality",
)

# Sample 5 outliers.
dataset.query().sampling().metadata_weighting(
    n_samples_to_select=5,
    sampling_result_tag_name="outlier_sampling",
    metadata_key="typicality",
    strength=-1
)
```

If your dataset has multiple embedding models, pass `embedding_model_name` to select which one to use. See [`Dataset.compute_typicality_metadata`](../api/dataset.md#lightly_studio.core.dataset.Dataset.compute_typicality_metadata) for the full API reference.

### Similarity

!!! tip "When to use"
    You have a few examples of something you want more of, such as a rare class, a specific scene, or
    a failure case, and want to mine the dataset for visually similar samples.

!!! info "How this differs from search in the GUI"
    The [text and image search](search_and_filter.md#search-in-gui) in the GUI is for **manually**
    mining the dataset from a single text prompt or image. Similarity sampling does the same idea
    **algorithmically**: its query is a **tag** (a whole set of reference samples, not one input),
    it runs unattended, and it can be **combined with other strategies** in one run. It also takes a
    `strength`, so you can pull *toward* one tag with a positive weight while pushing *away* from
    another tag with a negative weight (see below).

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
dataset.query().sampling().metadata_weighting(
    n_samples_to_select=10,
    sampling_result_tag_name="similar_to_query_sampling",
    metadata_key=metadata_name,
)
```

`metadata_name` is optional. When omitted, a unique name is generated automatically and returned. See [`Dataset.compute_similarity_metadata`](../api/dataset.md#lightly_studio.core.dataset.Dataset.compute_similarity_metadata) for the full API reference.

#### Positive and negative examples

To pull toward one tagged set while pushing away from another, use
[`EmbeddingSimilarityStrategy`](../api/sampling.md) inside a
[multi-strategy run](#combining-multiple-strategies): a positive `strength` prefers samples similar
to one tag, a negative `strength` avoids samples similar to another.

```py
import lightly_studio as ls
from lightly_studio.sampling.sampling_config import EmbeddingSimilarityStrategy

dataset = ls.ImageDataset.load("my-dataset")

# Tag a set of examples you want more of, and a set you want to avoid.
dataset.match(...).add_tag("want_more")
dataset.match(...).add_tag("avoid")

# Prefer samples similar to "want_more" and dissimilar to "avoid".
dataset.query().sampling().multi_strategies(
    n_samples_to_select=10,
    sampling_result_tag_name="mined_samples",
    sampling_strategies=[
        EmbeddingSimilarityStrategy(query_tag_name="want_more", strength=1.0),
        EmbeddingSimilarityStrategy(query_tag_name="avoid", strength=-1.0),
    ],
)
```

### Class balancing

!!! tip "When to use"
    Your annotated data is imbalanced and you want to control the class mix of the selected subset,
    for example ensuring you have enough "pedestrians" in a driving dataset.

Class balancing selects samples based on the distribution of annotation classes.

!!! note "Annotations required"
    This strategy requires the dataset to have [annotations](annotations.md). It is primarily designed for **object detection** annotations. Segmentation masks may produce unexpected results, as mask definitions can vary (e.g., all pixels of a class in a single mask vs. multiple masks per class).

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()

# Option 1: Balance classes uniformly (e.g. equal number of cats and dogs)
dataset.query().sampling().annotation_balancing(
    n_samples_to_select=50,
    sampling_result_tag_name="balanced_uniform",
    target_distribution="uniform",
)

# Option 2: Mirror the class distribution of the input set
dataset.query().sampling().annotation_balancing(
    n_samples_to_select=50,
    sampling_result_tag_name="balanced_input",
    target_distribution="input",
)

# Option 3: Define a specific target distribution (e.g. 20% cat, 80% dog)
dataset.query().sampling().annotation_balancing(
    n_samples_to_select=50,
    sampling_result_tag_name="balanced_custom",
    target_distribution={"cat": 0.2, "dog": 0.8},
)
```

The three `target_distribution` options are:

| Value | Behavior |
|---|---|
| `"uniform"` | Equal share for every class present in the dataset |
| `"input"` | Mirrors the class distribution of the candidate input set |
| `{class: ratio, ...}` | Explicit target ratios; must sum to 1.0 |

### Metadata balancing

!!! tip "When to use"
    Your data is concentrated on a few conditions and you want the selection spread over them
    evenly, for example equal amounts of every weather or every recording city. Unlike
    [class balancing](#class-balancing), this needs no annotations: it balances a metadata field
    you already have.

Metadata balancing selects samples based on the distribution of the values of one metadata field.
The field must be categorical, which means its values are strings or booleans. To rank samples by a
numeric field instead, use [metadata weighting](#metadata-weighting).

```py
import lightly_studio as ls

# Load your dataset
dataset = ls.ImageDataset.load_or_create()

# Option 1: Balance the values uniformly (e.g. equal amounts of every weather)
dataset.query().sampling().metadata_balancing(
    n_samples_to_select=50,
    sampling_result_tag_name="balanced_uniform",
    metadata_key="weather",
    target_distribution="uniform",
)

# Option 2: Mirror the value distribution of the input set
dataset.query().sampling().metadata_balancing(
    n_samples_to_select=50,
    sampling_result_tag_name="balanced_input",
    metadata_key="weather",
    target_distribution="input",
)

# Option 3: Define a specific target distribution (e.g. 30% sunny, 70% rainy)
dataset.query().sampling().metadata_balancing(
    n_samples_to_select=50,
    sampling_result_tag_name="balanced_custom",
    metadata_key="weather",
    target_distribution={"sunny": 0.3, "rainy": 0.7},
)
```

The `target_distribution` options are the same as for [class balancing](#class-balancing), but they
apply to the values of the metadata field:

| Value | Behavior |
|---|---|
| `"uniform"` | Equal share for every value present in the dataset |
| `"input"` | Mirrors the value distribution of the candidate input set |
| `{value: ratio, ...}` | Explicit target ratios; must sum to 1.0. The values without a ratio share the remainder |

Samples that have no value for the field stay available for selection, but the strategy does not
move the selection towards or away from them. To balance more than one field, combine one strategy
per field with [multiple strategies](#combining-multiple-strategies). Each field is then balanced on
its own, not over the combinations of their values.

## Running a sampling

You can run any strategy from the GUI for a quick, one-off selection, or from the Python API when you
need reusable, configurable, or combined sampling in code.

### In the GUI

Open the dialog from the `Menu` button in the top-right corner and select `Sampling`. The dialog
shows a dropdown with the sampling strategies available in the GUI. Specify the number of samples and
the tag name to store the result under. [Python](#in-python) supports more strategies and lets you
combine them.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/sampling_workflow.mp4" type="video/mp4">
</video>

### In Python

Each strategy is configured directly from a [`DatasetQuery`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery) via [`sampling()`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery.sampling). This works for image datasets, video datasets, and video-frame datasets returned by [`VideoDataset.frames()`](../api/dataset.md#lightly_studio.VideoDataset.frames). The sampled items are stored under the tag passed as `sampling_result_tag_name`, so you can filter or export them later. `sampling_result_tag_name` must be a tag name that does not yet exist in the dataset, unless it is the `preselected_tag_name` of the same run (see [Continuing from preselected samples](#continuing-from-preselected-samples)).

### Filtering before sampling

By default, sampling considers all samples in the dataset. You can narrow the candidate set first with `match()`, and the sampling will only consider the matching samples:

```py
import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField

dataset = ls.ImageDataset.load_or_create()

# Sample 10 diverse items from images with width >= 1920 only.
dataset.match(ImageSampleField.width >= 1920).sampling().diverse(
    n_samples_to_select=10,
    sampling_result_tag_name="diverse_hd",
)
```

Videos can be filtered and sampled using `VideoDataset.match(...).sampling()` and video frames can be sampled through `VideoDataset.frames().match(...).sampling()`:

```py
import lightly_studio as ls
from lightly_studio.core.dataset_query import VideoFrameSampleField

dataset = ls.VideoDataset.load("my_video_dataset")
frames = dataset.frames()

for frame in frames.match(VideoFrameSampleField.frame_number > 1):
    frame.metadata["score"] = float(frame.frame_number)

frames.match(VideoFrameSampleField.frame_number > 1).sampling().metadata_weighting(
    n_samples_to_select=5,
    sampling_result_tag_name="sampled_frames",
    metadata_key="score",
)
```

See [Search and Filter](search_and_filter.md#query-in-python) for more filtering options.

### Continuing from preselected samples

Use `preselected_tag_name` to select a new batch while taking an earlier batch into
account. The preselected samples influence the strategy but are not added to the new
result tag. `n_samples_to_select` is the number of new samples to select.

```py
sampling = dataset.query().sampling()

sampling.diverse(
    n_samples_to_select=100,
    sampling_result_tag_name="first_batch",
)
sampling.diverse(
    n_samples_to_select=100,
    sampling_result_tag_name="second_batch",
    preselected_tag_name="first_batch",
)
```

The preselected tag must belong to the sampled collection, and all of its samples must
be part of the query being sampled. The option is available on every sampling method,
including `multi_strategies()`.

To grow one tag instead of creating a new one per batch, pass the same name as both
`preselected_tag_name` and `sampling_result_tag_name`. The newly selected samples are
added to the existing tag, so it holds the whole selection after every run:

```py
sampling = dataset.query().sampling()

sampling.diverse(
    n_samples_to_select=100,
    sampling_result_tag_name="training_set",
)
# "training_set" holds 100 samples.

sampling.diverse(
    n_samples_to_select=100,
    sampling_result_tag_name="training_set",
    preselected_tag_name="training_set",
)
# "training_set" holds 200 samples.
```

### Video sequence sampling

To select clips instead of individual frames, set `selected_sequence_length` to
the number of frames per sequence (for example `50`). By default `selected_sequence_length` is
 `None` and individual frames are selected. Each video is split into non-overlapping sequences of that
length; trailing frames that do not fill a full sequence are dropped. Sampling then chooses among sequence
proxies (mean of the frame embeddings), and every frame of each chosen sequence is tagged.

`n_samples_to_select` counts **frames** and must be a multiple of `selected_sequence_length`.
The number of selected sequences is `n_samples_to_select / selected_sequence_length`.

```py
import lightly_studio as ls

dataset = ls.VideoDataset.load("my_video_dataset")
frames = dataset.frames()

# Select 2 sequences of 50 frames each (100 frames total).
frames.query().sampling().diverse(
    n_samples_to_select=100,
    sampling_result_tag_name="sequence_clips",
    selected_sequence_length=50,
)
```

Only diversity selection on video frame collections supports `selected_sequence_length`.

### Combining multiple strategies

You can combine several strategies into a single sampling run. All configured strategies are evaluated together and weighted by the `strength` parameter.

```py
import lightly_studio as ls
from lightly_studio.sampling.sampling_config import (
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
dataset.query().sampling().multi_strategies(
    n_samples_to_select=10,
    sampling_result_tag_name="multi_strategy_sampling",
    sampling_strategies=[
        MetadataWeightingStrategy(metadata_key="typicality", strength=1.0),
        EmbeddingDiversityStrategy(embedding_model_name="my_model_name", strength=2.0),
    ],
)
```

### Exporting the results

Every sampling run writes its result to the tag passed as `sampling_result_tag_name`. You can export those samples from the GUI, or query them in Python by matching on the tag.

```py
import lightly_studio as ls
from lightly_studio.core.dataset_query import ImageSampleField

dataset = ls.ImageDataset.load("my-dataset")

sampled_items = (
    dataset.match(ImageSampleField.tags.contains("diverse_sampling")).to_list()
)

with open("export.txt", "w") as f:
    for sample in sampled_items:
        f.write(f"{sample.file_path_abs}\n")
```

For more details on filtering by tag or exporting subsets, see [Search and Filter](search_and_filter.md#query-in-python) and [Export](export.md).
