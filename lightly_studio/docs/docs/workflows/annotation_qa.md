---
title: Find Wrong Annotations in Your Dataset
description: Three ways to check annotation quality in LightlyStudio - skim the annotation grid, look for outliers in the embedding plot, and compare your annotations against a baseline annotation source.
---

# Find Wrong Annotations

Wrong annotations make your model worse, and opening images one at a time is no way to find them.
This page shows three ways to check your annotations in the GUI.

## What Goes Wrong

Four kinds of mistake show up in almost every dataset:

- **Wrong class.** The annotation marks the right object, but carries the wrong class: a cat
  annotated as a dog.
- **Imprecise region.** The class is right, but the box or mask does not follow the object. It is
  too large, too small, or sits off to one side.
- **Extra annotation.** There is an annotation, but nothing under it to annotate.
- **Missing annotation.** The image shows a cat, and nothing marks it. Your model learns that the
  cat is background.

Each method below finds some of them, and needs something different to work:

| Method | What it finds | What you need |
|---|---|---|
| [Scan the annotation grid](#scan-the-annotation-grid) | Wrong class, imprecise region, extra annotation | Annotations |
| [Scan the embedding plot](#scan-the-embedding-plot) | Wrong class, also in classes too large to scroll through | Annotation crop embeddings |
| [Compare two annotation sources](#compare-two-annotation-sources) | Missing annotation, imprecise region | A second annotation source and an evaluation run |

A missing annotation is in neither the grid nor the plot, because there is nothing to show. Only
the third method finds it, by asking a second source what it sees. Use the methods together.

## Fixing What You Find

All three methods end the same way: with annotations you want to correct. To edit them, enter
editing mode with `Edit Annotations`.

- **Change the class of many annotations at once.** Select the tiles in the annotation grid. The
  `Selected annotations` panel on the right shows how many you picked. Choose the right class under
  `Select a class`, and every selected annotation gets it.
- **Edit a single annotation.** Open the annotation or its sample in detail view and correct the
  class or the region there (see [Annotations](annotations.md)).
- **Tag it for a relabeling batch.** If somebody else makes the correction, tag the samples and
  share the tag (see [Tags](../core_concepts/tags.md)).

## Scan the Annotation Grid

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_0_annotation_grid_online.mp4" 
  type="video/mp4">
</video>

The `Annotations` view shows one tile per annotation instead of one tile per sample. Annotations
that mark a region appear as that region, cropped out of the image, and classifications use the
whole image. You see what every annotation covers without opening a single full image.

Filter the grid down to one class, and everything that does not belong stands out.

1. Open the `Annotations` view for the annotation source you want to check.
2. In the left sidebar, filter `Annotation classes` down to a single class.
3. Scroll through the grid. Every tile should show the same kind of thing, so a bicycle among the
   cars or a tile that is mostly background is easy to spot.
4. Repeat for the next class.

## Scan the Embedding Plot

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_1_embedding_plot_online.mp4" type="video/mp4">
</video>

LightlyStudio embeds each annotation crop on its own, so the embedding plot puts annotations that
look alike next to each other. Annotations of one class therefore gather in one region of the plot.
An annotation from another class in that region looks like its neighbors, so it may be annotated
wrong.

!!! info "Requires annotation crop embeddings"

    This method needs embeddings for the annotation crops, not just for the samples. LightlyStudio
    computes them for the annotations that exist at that moment, so a dataset whose annotations
    were added later may have none. See
    [Embeddings](../core_concepts/embeddings.md#object-level-embeddings) for how crop embeddings
    are computed and how to trigger them.

1. In the `Annotations` view, open the embedding plot with the `Embed` button in the top right.
2. Set the `Color by` popover to annotation class. Each class now has its own color.
3. Find a cluster where one color clearly dominates. That cluster is one class's region of the
   plot, and the dominant color tells you which class it is.
4. Lasso the cluster. The annotation grid now shows only the annotations inside it.
5. In the left sidebar, filter `Annotation classes` to every class **except** the dominant one.
   What remains looks like the dominant class but carries a different annotation class.
6. Inspect the remaining tiles and correct the ones that are wrong.
7. Repeat for the next cluster.

Sitting close in the plot makes an annotation a candidate, not a mistake. Classes that look alike
overlap in the plot, so a correct annotation can land inside another class's region.

## Compare Two Annotation Sources

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/annotation_qa_2_model_eval_online.mp4" type="video/mp4">
</video>

The first two methods rely on your eyes. This one gets a second opinion: it compares your
annotations against a baseline annotation source, such as a foundation model run over the same
images. Where the two disagree, one of them is wrong.

Run a [model evaluation](evaluation.md) with your annotations on one side and the baseline on the
other. The run scores how well the two agree and stores the score, so you can sort by it and start
where they disagree most.

1. Create the evaluation run with your annotation source as ground truth and the baseline as
   predictions (see [Model Evaluation in Python](evaluation.md#model-evaluation-in-python)).
2. Browse your own annotation source. The sort control only offers a run's metrics while you browse
   one of the two sources that run compared.
3. Sort so the strongest disagreement comes first. Where the score sits, and which way to sort,
   depends on the annotation type:

    | Annotation type | Sort | Order |
    |---|---|---|
    | Object detection | the annotation grid by `<run name>.iou` | ascending |
    | Classification | the sample grid by `disagreement` | descending |
    | Semantic segmentation | the sample grid by `miou` | ascending |

4. Inspect what comes up. A strong disagreement means the two sources see the image differently. It
   does not say which of the two is right.

Browsing the baseline source instead of your own shows you where the model differs from your
annotations. You can use it to find missing annotations.

!!! warning "Unmatched annotations have no score"

    In an object detection run, an annotation that the other source found no counterpart for gets
    no value at all, and annotations without a value sort to the **end** of the grid in both
    directions. That is where the objects only one side found end up, so check the bottom of the
    grid as well as the top.

Editing annotations makes the evaluation run stale. The sort control then shows a warning icon next
to it. Click `Recompute evaluation` to bring the order back in step with your edits.

## Next Steps

- [Annotations](annotations.md): create, edit, and import annotations.
- [Model Evaluation](evaluation.md): the full evaluation workflow, including the confusion matrix.
- [Curate a Traffic CCTV Dataset for YOLO Training](../tutorials/yolo-traffic-cctv-object-detection.md): a worked example that includes a grid-based QA pass on a real dataset.
