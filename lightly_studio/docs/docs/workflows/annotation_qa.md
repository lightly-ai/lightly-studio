---
title: Find Wrong Annotations in Your Dataset
description: Three ways to check annotation quality in LightlyStudio - skim the annotation grid, look for outliers in the embedding plot, and compare your annotations against a baseline annotation source.
---

# Annotation QA

Wrong annotations reduce model quality. Opening images one at a time makes them difficult to find.
This page describes three ways to check annotations in the GUI. The methods require annotations,
annotation crop embeddings, or a second annotation source, respectively.

| Method | What you need | What it catches |
|---|---|---|
| [Scan the annotation grid](#scan-the-annotation-grid) | Annotations | Wrong annotation class, obviously bad boxes |
| [Scan the embedding plot](#scan-the-embedding-plot) | Annotation crop embeddings | Annotations that sit inside another class's region |
| [Compare two annotation sources](#compare-two-annotation-sources) | A second annotation source and an evaluation run | Boxes that disagree with a trusted baseline |

The three methods identify different types of problems and can be used together.

## Fixing What You Find

Each method can identify annotations that need correction. To edit them, enter editing mode with
`Edit Annotations`.

- **Change the class of many annotations at once.** Select the affected tiles in the annotation
  grid. The `Selected annotations` panel on the right shows how many you picked; choose the right
  class under `Select a class` and every selected annotation gets it. The change is undoable.
- **Edit a single annotation.** Open the annotation or its sample in detail view and correct the
  class or the box geometry there. See [Annotations](annotations.md).
- **Tag it for a relabeling batch.** If someone else needs to make the correction, tag the samples
  and share the tag. See [Tags](../core_concepts/tags.md).

## Scan the Annotation Grid

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_grid.mp4" type="video/mp4">
</video>

The `Annotations` view shows one tile per annotation instead of one tile per sample. Object
detection and segmentation annotations appear as cropped image regions, while classifications use
the whole image. This view makes it possible to inspect the annotated regions without opening each
full image.

To use it as a QA pass:

1. Open the `Annotations` view for the annotation source you want to check.
2. In the left sidebar, filter `Annotation classes` down to a single class.
3. Scroll through the grid. Since all tiles should belong to the same class, incorrect classes and
   oversized boxes are easier to identify. Examples include a bicycle among the cars or a crop that
   is mostly background.
4. Repeat for the next class.

## Scan the Embedding Plot

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_embedding.mp4" type="video/mp4">
</video>

Annotation crops are embedded individually, so the embedding plot places visually similar
annotations near one another. Annotations of the same class often gather in the same region of the
plot. An annotation from another class in that region may be incorrectly classified.

!!! info "Requires annotation crop embeddings"

    This method needs embeddings for the annotation crops, not just for the samples. LightlyStudio
    computes them for the annotations that exist when the crops are embedded, so a dataset whose
    annotations were added later may have none. See
    [Embeddings](../core_concepts/embeddings.md#object-level-embeddings) for how crop embeddings
    are computed and how to trigger them.

To use it as a QA pass:

1. In the `Annotations` view, open the embedding plot with the `Embed` button in the top right.
2. Set the `Color by` popover to annotation class. Each class now has its own color.
3. Find a cluster where one color clearly dominates. That cluster is one class's region of the
   plot, and the dominant color tells you which class it is.
4. Lasso the cluster. The annotation grid now shows only the annotations inside it.
5. In the left sidebar, filter `Annotation classes` to every class **except** the dominant one.
   The remaining annotations look like the dominant class but have a different annotation class.
6. Inspect the remaining tiles and correct the annotations that are wrong.
7. Repeat for the next cluster.

Proximity in the plot helps identify candidates but does not prove that an annotation is wrong.
Classes that look alike can overlap in embedding space, and a correctly classified annotation can
appear inside another class's region. Inspect the candidates before correcting them.

## Compare Two Annotation Sources

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_evaluation_sort.mp4" type="video/mp4">
</video>

The first two methods rely on visual inspection. This method compares your annotations with a
baseline annotation source. A foundation model run on the same images can provide a suitable
baseline. Differences between the two sources indicate annotations that may need inspection.

Run a [model evaluation](evaluation.md) with your annotations as one side and the baseline as the
other. Object detection evaluation matches boxes by intersection over union (IoU) and stores the
IoU of each matched pair on the annotation itself, which lets you sort the annotation grid by it.

!!! note "Object detection only"

    Only object detection writes a per-annotation metric. Classification and semantic segmentation
    store their metrics per sample, so there you sort the sample grid by `disagreement` or `miou`
    instead. See [Model Evaluation](evaluation.md#model-evaluation-in-the-gui).

To use it as a QA pass:

1. Create the evaluation run with your annotation source as ground truth and the baseline as
   predictions. See [Model Evaluation in Python](evaluation.md#model-evaluation-in-python).
2. Open the `Annotations` view on your own annotation source. The sort control only offers a run's
   metrics while you browse one of the two sources that run compared.
3. Sort by `<run name>.iou` ascending. Boxes with the largest difference from the baseline appear
   first.
4. Inspect the boxes in the grid. A low IoU indicates that the two sources disagree about the
   object location; it does not indicate which box is correct.

Browsing the baseline source instead of your own shows where the model differs from your
annotations. Both sorts use the same run.

!!! warning "Unmatched annotations have no IoU"

    An annotation the baseline found no counterpart for gets no IoU value at all, and annotations
    without a value sort to the **end** of the grid in both directions. These cases can indicate
    objects found by only one side, so inspect the bottom of the grid as well as the top.

Editing annotations makes the evaluation run stale. The sort control then shows a warning icon next
to it; click `Recompute evaluation` to bring the order back in step with your edits.

## Next Steps

- [Annotations](annotations.md) — create, edit, and import annotations.
- [Model Evaluation](evaluation.md) — the full evaluation workflow, including the confusion matrix.
- [Curate a Traffic CCTV Dataset for YOLO Training](../tutorials/yolo-traffic-cctv-object-detection.md)
  — a worked example that includes a grid-based QA pass on a real dataset.
