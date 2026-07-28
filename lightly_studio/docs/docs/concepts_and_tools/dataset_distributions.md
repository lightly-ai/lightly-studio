---
title: Visualize Dataset Distributions in LightlyStudio
description: Visualize annotation class distributions and numeric or categorical metadata in LightlyStudio to find class imbalance, coverage gaps, and missing data.
---

# Visualize Dataset Distributions in LightlyStudio

Dataset distributions summarize the samples and annotations in your current dataset view. Use them
to spot class imbalance, coverage gaps, and missing metadata before training or evaluating a model.

## Explore Distributions in the GUI

Open an image dataset and click **Distr** to open the **Distribution** panel. Choose
**Annotation classes** or **Metadata**, then select the annotation type or metadata key you want to
inspect.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/dataset-distribution-overview.mp4" type="video/mp4">
</video>

The plots respond to active filters, so you can inspect the complete dataset or a filtered subset.

## Annotation Class Distributions

The annotation class distribution shows how annotations are distributed across classes. It supports
[classification, object detection, and segmentation annotations](annotations.md).

Use **Annotation type** to inspect one annotation type or all available types together. In the chart
settings, use **Count by** to choose what the bars represent:

- **Objects** counts individual annotations, such as bounding boxes or segmentation masks.
- **Samples** counts distinct images containing each annotation class.

You can also choose which classes to show, sort them by count or name, change the chart orientation,
and expand the chart. These views help identify dominant, rare, and long-tail classes.

## Metadata Distributions

Select **Metadata**, then choose the metadata key you want to inspect.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/dataset-distribution-metadata.mp4" type="video/mp4">
</video>

### Numeric Metadata

Numeric metadata fields, such as temperature, brightness, confidence, or blur score, are shown as
histograms.

Change the number of bins to adjust the level of detail. Click a bin or drag across multiple bins to
filter the dataset to that range. Select the same range again to clear the filter.

### Categorical Metadata

Categorical metadata fields, such as city, camera ID, production line, weather, or a boolean review
status, are shown as bar charts.

Select one or more values to filter the dataset. **Missing** represents samples without a value for
the selected key. **Other** groups values outside the most frequent values shown in the chart and
cannot be selected.

## Required Dataset Content

The available distributions depend on what your dataset contains:

| Distribution | Required content |
| --- | --- |
| Annotation classes | Classification, object detection, or segmentation annotations |
| Numeric metadata | Integer or floating-point sample metadata |
| Categorical metadata | String or boolean sample metadata |

If a distribution is not available, add the corresponding
[annotations](annotations.md) or [metadata](metadata.md) to the dataset. See
[Search and Filter](search_and_filter.md) for the other ways to narrow down the samples shown in
the dataset view.
