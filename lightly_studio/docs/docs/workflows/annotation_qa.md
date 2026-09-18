---
title: Find Wrong Annotations in Your Dataset
description: Three ways to check annotation quality in LightlyStudio - skim the annotation grid, look for outliers in the embedding plot, and compare your annotations against a baseline annotation source.
---

# Annotation QA

Wrong annotations cost you model quality, and they are hard to find by opening images one at a
time. This page covers three ways to find them in the GUI, from the one that needs nothing beyond
your annotations to the one that needs a second opinion to compare against. This is what is often
called label QA or label error detection.

| Method | What you need | What it catches |
|---|---|---|
| [Scan the annotation grid](#scan-the-annotation-grid) | Annotations | Wrong annotation class, obviously bad boxes |
| [Scan the embedding plot](#scan-the-embedding-plot) | Annotation crop embeddings | Annotations that sit inside another class's region |
| [Compare two annotation sources](#compare-two-annotation-sources) | A second annotation source and an evaluation run | Boxes that disagree with a trusted baseline |

The three methods find different problems, so they add up rather than replace each other. Start
with the grid, which costs you nothing but a few minutes of scrolling.

## Fixing What You Find

All three methods end the same way: you are looking at an annotation that is wrong. You have three
ways to deal with it, and they all need editing mode, which you enter with `Edit Annotations`.

- **Change the class of many annotations at once.** Select the affected tiles in the annotation
  grid. The `Selected annotations` panel on the right shows how many you picked; choose the right
  class under `Select a class` and every selected annotation gets it. The change is undoable.
- **Edit a single annotation.** Open the annotation or its sample in detail view and correct the
  class or the box geometry there. See [Annotations](annotations.md).
- **Tag it for a relabeling batch.** If the fix needs a human who is not you, tag the samples and
  hand over the tag instead of a list of file names. See [Tags](../core_concepts/tags.md).

## Scan the Annotation Grid

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_grid.mp4" type="video/mp4">
</video>

The `Annotations` view shows one tile per annotation rather than one tile per sample. Object
detection and segmentation annotations appear as the cropped image region, classifications as the
whole image. Scrolling through a wall of crops is a much faster way to spot a wrong annotation than
paging through full images, because every tile shows you the object and nothing else.

To use it as a QA pass:

1. Open the `Annotations` view from the navigation menu.
2. Pick the annotation source you want to check in the source selector.
3. In the left sidebar, filter `Annotation classes` down to a single class.
4. Scroll. A grid of one class is visually uniform, so anything that does not belong stands out
   without you having to look for it — a bicycle among the cars, or a crop that is mostly
   background because the box is far too large.
5. Repeat for the next class.

One class at a time is what makes this work. A mixed grid gives your eye nothing to compare
against, and the mistakes stop being obvious.

## Scan the Embedding Plot

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_embedding.mp4" type="video/mp4">
</video>

Annotation crops are embedded individually, so the embedding plot places each annotation next to
the annotations that look like it. Annotations of one class therefore gather in the same region of
the plot. An annotation of a different class sitting inside that region is an annotation that looks
like its neighbours but is not labeled like them — which is what a wrong annotation class looks
like from the outside.

!!! info "Requires annotation crop embeddings"

    This method needs embeddings for the annotation crops, not just for the samples. LightlyStudio
    computes them for the annotations that exist when the crops are embedded, so a dataset whose
    annotations were added later may have none. See
    [Embeddings](../core_concepts/embeddings.md#object-level-embeddings) for how crop embeddings
    are computed and how to trigger them.

To use it as a QA pass:

1. Open the embedding plot with the `Embed` button in the top right.
2. Set the `Color by` popover to annotation class. Each class now has its own color.
3. Find a region where one color dominates. You can also filter to a single class first and use
   the resulting cluster to see where that class lives in the plot.
4. Look for points of a different color inside that region. Double-click a legend entry to isolate
   a class, which makes stray points much easier to see.
5. Lasso the region to scope the grid to those annotations, then inspect them as tiles.

Proximity in the plot ranks candidates for you; it does not prove that an annotation is wrong.
Classes that genuinely look alike overlap in embedding space, and a correctly labeled annotation
can sit well inside another class's region. Treat what you find as a shortlist to look at, not as
a list of errors.

## Compare Two Annotation Sources

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_evaluation_sort.mp4" type="video/mp4">
</video>

The first two methods rely on your eye. This one relies on a second opinion: a baseline annotation
source you compare your annotations against. A strong foundation model run over the same images
works well as that baseline — you are not trusting it to be right, you are using disagreement
between the two as a signal that one of them is worth a look.

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
3. Sort by `<run name>.iou` ascending. Your worst-matching boxes come first: the ones the baseline
   put somewhere noticeably different.
4. Work down the grid. A low IoU means the two disagree about where the object is; either box can
   be the wrong one, which is why you look rather than fix blindly.

Browsing the baseline source instead of your own answers the opposite question — where the model
is wrong rather than where your annotations are. Both sorts use the same run.

!!! warning "Unmatched annotations have no IoU"

    An annotation the baseline found no counterpart for gets no IoU value at all, and annotations
    without a value sort to the **end** of the grid in both directions. These are often the most
    interesting cases — an object only one side found — so scroll to the bottom of the grid as
    well as reading the top.

Editing annotations makes the evaluation run stale. The sort control then shows a warning icon next
to it; click `Recompute evaluation` to bring the order back in step with your edits.

## Next Steps

- [Annotations](annotations.md) — create, edit, and import annotations.
- [Model Evaluation](evaluation.md) — the full evaluation workflow, including the confusion matrix.
- [Curate a Traffic CCTV Dataset for YOLO Training](../tutorials/yolo-traffic-cctv-object-detection.md)
  — a worked example that includes a grid-based QA pass on a real dataset.
