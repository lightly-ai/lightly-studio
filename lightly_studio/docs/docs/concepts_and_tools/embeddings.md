---
title: Understand Image and Video Embeddings in LightlyStudio
description: Embeddings power search, the embedding plot, and sampling in LightlyStudio. They are computed automatically when you add data, and you can supply your own.
---

# Embeddings

An embedding is a vector of numbers that captures the visual content of a sample.
Samples that look alike get vectors that are close together, so distance in
embedding space is a measure of visual similarity.

Embeddings are the shared foundation under three features in LightlyStudio:
[search](search_and_filter.md), the embedding plot, and every embedding-based
[sampling](sampling.md) strategy. You do not run anything to get them — LightlyStudio
computes embeddings **automatically** when you add data.

## How Embeddings Are Created

LightlyStudio embeds each sample when you add it to a dataset with all loading functions,
for example with `add_images_from_path` for an [image dataset](../dataset_setup/image_dataset.md) or
`add_videos_from_path` for a [video dataset](../dataset_setup/video_dataset.md).

To skip embedding, pass `embed=False` to the add method. This is faster, but it
disables search and the embedding plot for those samples.

Embeddings are stored in the database and reused when you reopen the
dataset. Only new samples are embedded. See
[Reuse Datasets](../dataset_setup/reuse_datasets.md).

Beyond whole images and videos, LightlyStudio embeds two more levels of your data.

### Video frame embeddings

For a video dataset, LightlyStudio embeds each video as a whole and also embeds the
extracted frames as images. Frame embeddings let you search and plot single frames,
just like images. They are on by default; pass `embed_frames=False` to
`add_videos_from_path` to skip them.

### Object-level embeddings

LightlyStudio embeds each object — an object-detection box or segmentation mask — as
its own crop. This unlocks the embedding plot and similarity search on individual
objects, the same way they work for whole images. Browse objects in the `Annotations`
view of the GUI.

Object embeddings are on by default; the `add_annotations_from_*` methods accept
`embed_annotations=False` to skip them.

!!! warning "Editing an annotation does not update its embedding"
    An object keeps the embedding of its original crop. If you move or resize a box,
    LightlyStudio does **not** recompute its embedding. Support for this is planned.

## Built-in Embedding Models

LightlyStudio ships with two embedding models:

- **MobileCLIP** (`mobileclip_s0`, 512 dimensions) — the default for images.
- **Perception Encoder** (`PE-Core-T16-384`) — the default for video.

## The Embedding Plot (GUI)

Click the `Embed` button in the top right of the GUI to open the embedding plot. It
shows your samples as points in a 2D projection of embedding space (projected with PaCMAP).

![Embedding plot](https://storage.googleapis.com/lightly-public/studio/docs/embedding_plot_v1.0.4.png){ width="100%" }

You can:

- **Color the points** by tag, annotation class, or metadata (text and true/false
  fields) using the `Color by` popover.
- **Hover a point** to preview its thumbnail.
- **Lasso a region** to scope the grid to the samples in that part of the plot, and
  show or hide the points that your current filters exclude.
- **Double-click a legend entry** to isolate that category — only its points
  stay visible. Single-click to toggle a category visibility.


## What Embeddings Power

- **Similarity search** by text or image — see [Search and Filter](search_and_filter.md).
- **Sampling** strategies such as diverse, deduplication, similarity, and
  typicality/outliers — see [Sampling](sampling.md).

<!-- TODO(Michal, 08/2026) ## Using Your Own Embeddings -->
