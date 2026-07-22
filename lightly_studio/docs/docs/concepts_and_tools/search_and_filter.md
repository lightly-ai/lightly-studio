---
title: Search and Filter Images by Similarity
description: Find visually and semantically similar images with text or image search, then filter datasets by tags, annotations, and metadata in LightlyStudio.
---

# Search and Filter

Search helps you find visually or semantically similar samples from a text or image. Filters narrow down the samples currently shown in the view by tags, annotations, dimensions, and other numeric metadata.

For more complex filtering, use the query feature — either in the GUI query editor or in Python when you need reusable filtering, sorting, and slicing.

## Search in GUI

Use the search bar above the grid to find similar samples in one of these ways:

1. Type a text query.
2. Paste an image from your clipboard into the search bar. You can e.g. right-click an image in your browser and select `Copy image`, then click the search bar and paste it with `Ctrl+V` or `Cmd+V`.
3. Click the image button to upload an image.

Then submit the search by hitting `Enter`. The number shown on each search result is its similarity score to the current query. Click the `x` button to remove the search query.

The screen recording below shows the search both by text query "dog" and by pasting an image.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/search_filter_search_v4.mp4" type="video/mp4">
</video>

!!! note "Search requires embeddings"
    Search is available only when embeddings were generated during data loading.

Search works the same way in the `Annotations` view, where it finds similar objects using
object-level embeddings. See
[Object-level embeddings](annotations.md#object-level-embeddings) for details.

## Filter in GUI

The left sidebar combines the most common ways to narrow down the visible samples:

- `Tags`: Click one or more tags to focus on the subset you care about, such as `labeled` or `unlabeled`.
- `Annotation classes`: Click one or more annotation classes to show items with those annotations.
- `Dimensions`: Use `Width` and `Height` to constrain the visible item size.
- `Metadata`: If numeric metadata fields are available, they appear as additional sliders in the same area.

![Tag filters](https://storage.googleapis.com/lightly-public/studio/docs/search_filter_tags_v1.0.0.png){ width="100%"}


For videos, the sidebar adds `Duration`. If the videos in the current view contain varying frame rates, it also shows `FPS`.

![Video filters](https://storage.googleapis.com/lightly-public/studio/search_filter_videos_v4.jpg){ width="100%" }

## Query in GUI

!!! warning "Query in GUI is currently available for image datasets only."

Your dataset can be filtered by a custom query written in an SQL-like language. Open the
query editor by clicking the `Add query filter` button in the left sidebar.

![Query filter](https://storage.googleapis.com/lightly-public/studio/docs/search_filter_query_v1.0.0.png){ width="100%" }

The language supports filtering by image fields such as dimensions or file name, tags, annotations,
as well as logical combinations of these. For a full reference, see the
[Lightly Query Language](lightly_query_language.md) documentation.

Example queries:

```mysql
# Images that are at least 640 pixels wide or 400 pixels tall
width >= 640 OR height >= 400

# Images which do not have the tag "reviewed"
NOT "reviewed" IN tags

# Images with a "car" segmentation mask that is less than 100 pixels wide
segmentation_mask(class_name = "car" AND width < 100)
```

## Query in Python

You can programmatically filter samples by attributes (e.g., image size, tags) or annotations (object detections, classifications and segmentation masks), sort them, and select subsets. This is useful for creating training/validation splits, finding specific samples, or exporting filtered data.

Create a query object by combining [`match`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery.match), [`order_by`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery.order_by) and [`slice`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery.slice) (or [`[start:end]`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery.__getitem__)) calls. The query is composed lazily and executed against the database once it is consumed, e.g. by iterating over it or calling [`add_tag`](../api/dataset_query.md#lightly_studio.core.dataset_query.dataset_query.DatasetQuery.add_tag).

The example below uses the [`ImageSampleField`](../api/dataset_query.md#imagesamplefield) for
sample-level filtering; for video datasets, use
[`VideoSampleField`](../api/dataset_query.md#videosamplefield) instead. It also uses
[`ObjectDetectionField`](../api/dataset_query.md#objectdetectionfield) to demonstrate annotation
filtering. For the other annotation types, see
[`ClassificationField`](../api/dataset_query.md#classificationfield) and
[`SegmentationMaskField`](../api/dataset_query.md#segmentationmaskfield). For filtering by
evaluation run metrics, see
[`SampleEvaluationQuery`](../api/dataset_query.md#sampleevaluationquery) and
[`EvaluationMetricField`](../api/dataset_query.md#evaluationmetricfield) in the reference below.
```py
from lightly_studio.core.dataset_query import (
    AND,
    NOT,
    OR,
    ImageSampleField,
    OrderByField,
    ObjectDetectionField,
    ObjectDetectionQuery,
)

# QUERY: Define a lazy query, composed by: match, order_by, slice

# match: Find all samples that need labeling plus small samples (< 500px) that haven't been reviewed.
# For video datasets: use VideoSampleField instead of ImageSampleField.
query = dataset.match(
    OR(
        AND(
            ImageSampleField.width < 500,
            NOT(ImageSampleField.tags.contains("reviewed"))
        ),
        ImageSampleField.tags.contains("needs-labeling")
    )
)
# match (with annotations): Samples with at least one confident "person" detection
# larger than 100 px tall, in an image with 500 px or more width.
query = dataset.match(
    AND(
        ImageSampleField.width >= 500,
        # Criteria inside annotation filters are combined using AND(..) operator
        ObjectDetectionQuery(
            ObjectDetectionField.class_name == "person",
            ObjectDetectionField.source == "predictions",
            ObjectDetectionField.confidence >= 0.8,
            ObjectDetectionField.height >= 100,
        )
    )
)

# order_by: Sort the samples by their width descending.
query.order_by(
    OrderByField(ImageSampleField.width).desc()
)

# slice: Extract a slice of samples.
query[10:20]

# chaining: The query can also be constructed in chained way
query = dataset.match(...).order_by(...)[...]

# Ways to consume the query
# Tag this subset for easy filtering in the UI.
query.add_tag("needs-review")

# Iterate over resulting samples
for sample in query:
    # Access sample attributes such as tags, file_name, or metadata

# Collect all resulting samples as list
samples = query.to_list()

# Export all resulting samples in coco format
dataset.export(query).to_coco_object_detections()
# For video datasets: export in a video format
# dataset.export(query).to_youtube_vis_segmentation_mask()

```

### Reference

The following sections explain the available methods for defining a query in more detail.
Examples use [`ImageSampleField`](../api/dataset_query.md#imagesamplefield) for sample-level
filters and the annotation query helpers for annotation-level filters. For video datasets, the
sample-level examples translate to [`VideoSampleField`](../api/dataset_query.md#videosamplefield).

=== "`match`"

    You can define query filters with:
    ```py
    query.match(<expression>)
    ```

    #### Sample queries

    Sample-level queries use the `ImageSampleField.<field_name> <operator> <value>` syntax.
    Available field names can be seen in
    [`ImageSampleField`](../api/dataset_query.md#lightly_studio.core.dataset_query.image_sample_field.ImageSampleField).

    ```py
    from lightly_studio.core.dataset_query import ImageSampleField

    # Ordinal fields: <, <=, >, >=, ==, !=
    expr = ImageSampleField.height >= 10            # All samples with images that are taller than 9 pixels
    expr = ImageSampleField.width == 10             # All samples with images that are exactly 10 pixels wide
    expr = ImageSampleField.created_at > datetime   # All samples created after datetime (actual datetime object)

    # String fields: ==, !=
    expr = ImageSampleField.file_name == "some"     # All samples with "some" as file name
    expr = ImageSampleField.file_path_abs != "other" # All samples that are not having "other" as file_path

    # Tags: contains()
    expr = ImageSampleField.tags.contains("dog")    # All samples that contain the tag "dog"

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```

    #### Annotation queries

    Annotation queries use `ClassificationQuery(...)`, `ObjectDetectionQuery(...)`, and
    `SegmentationMaskQuery(...)`. Each helper matches a sample when it has at least one
    annotation of that type that satisfies all passed criteria.

    ```py
    from lightly_studio.core.dataset_query import (
        ClassificationField,
        ClassificationQuery,
        ObjectDetectionField,
        ObjectDetectionQuery,
        SegmentationMaskField,
        SegmentationMaskQuery,
    )

    # Classification fields: class_name, source, confidence
    expr = ClassificationQuery(
        ClassificationField.class_name == "approved",
        ClassificationField.source == "ground_truth",
        ClassificationField.confidence >= 0.9,
    )

    # Object detection fields: class_name, source, confidence, x, y, width, height
    expr = ObjectDetectionQuery(
        ObjectDetectionField.class_name == "person",
        ObjectDetectionField.source == "predictions",
        ObjectDetectionField.confidence >= 0.8,
        ObjectDetectionField.x >= 10,
        ObjectDetectionField.y >= 20,
        ObjectDetectionField.width >= 40,
        ObjectDetectionField.height >= 100,
    )

    # Segmentation mask fields: class_name, source, confidence, x, y, width, height
    expr = SegmentationMaskQuery(
        SegmentationMaskField.class_name == "road",
        SegmentationMaskField.source == "ground_truth",
        SegmentationMaskField.confidence >= 0.95,
        SegmentationMaskField.x >= 0,
        SegmentationMaskField.y >= 0,
        SegmentationMaskField.width >= 300,
        SegmentationMaskField.height >= 80,
    )

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```

    #### Sample evaluation queries

    Sample evaluation queries use `SampleEvaluationQuery(...)` together with
    `EvaluationMetricField(...)` to filter samples by metrics from a specific evaluation run.
    They match only samples that are part of the named run and satisfy all passed metric
    criteria.

    ```py
    from lightly_studio.core.dataset_query import (
        AND,
        EvaluationMetricField,
        ImageSampleField,
        SampleEvaluationQuery,
    )

    # Metric operators: <, <=, >, >=, ==, !=
    expr = SampleEvaluationQuery(
        "run1",
        EvaluationMetricField("score") > 0.5,
    )

    # Multiple metrics inside SampleEvaluationQuery are combined with AND
    expr = SampleEvaluationQuery(
        "run1",
        EvaluationMetricField("precision") > 0.5,
        EvaluationMetricField("recall") > 0.5,
    )

    # Evaluation queries can be combined with sample-level filters
    expr = AND(
        ImageSampleField.tags.contains("reviewed"),
        SampleEvaluationQuery(
            "run1",
            EvaluationMetricField("score") >= 0.8,
        ),
    )

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```

    #### Annotation evaluation queries

    Use `AnnotationMetricQuery` to filter samples by annotation-level results from a specific
    [evaluation run](evaluation.md). For matched ground-truth and prediction pairs, use
    `AnnotationMetricQuery.confusion(...)`, optionally together with
    `AnnotationEvaluationMetricField(...)`. The example below finds samples where `cat` got
    confused as a `dog` and the IoU is greater than 0.3.

    ```py
    from lightly_studio.core.dataset_query import (
        AnnotationEvaluationMetricField,
        AnnotationMetricQuery,
    )

    expr = AnnotationMetricQuery.confusion(
        "run1",
        "cat",
        "dog",
        AnnotationEvaluationMetricField("iou") > 0.3,
    )

    # Assign the expression to a query:
    query.match(expr)
    ```

    To filter samples with unmatched predictions or missed ground truths, use `AnnotationMetricQuery.false_positive(...)` and `AnnotationMetricQuery.false_negative(...)`.

    ```py
    from lightly_studio.core.dataset_query import AnnotationMetricQuery

    # Samples where the model predicted a dog that did not match any ground truth.
    expr = AnnotationMetricQuery.false_positive(
        run_name="run1",
        prediction="dog",
    )

    # Samples where a ground-truth cat was not matched by any prediction.
    expr = AnnotationMetricQuery.false_negative(
        run_name="run1",
        ground_truth="cat",
    )

    # Assign either expression to a query:
    query.match(expr)
    ```

    #### Boolean operators
    The filtering on individual fields can flexibly be combined to create more complex match expression. For this, the boolean operators `AND`, `OR`, and `NOT` are available. Boolean operators can arbitrarily be nested.


    ```py
    from lightly_studio.core.dataset_query import (
        AND,
        NOT,
        OR,
        ImageSampleField,
        ObjectDetectionField,
        ObjectDetectionQuery,
    )

    # All samples with images that are between 10 and 20 pixels wide
    expr = AND(
        ImageSampleField.width > 10,
        ImageSampleField.width < 20
    )

    # All samples with file names that are either "a" or "b"
    expr = OR(
        ImageSampleField.file_name == "a",
        ImageSampleField.file_name == "b"
    )

    # All samples which do not contain a tag "dog"
    expr = NOT(ImageSampleField.tags.contains("dog"))

    # All samples for a nested expression
    expr = OR(
        ImageSampleField.file_name == "a",
        ImageSampleField.file_name == "b",
        AND(
            ImageSampleField.width > 10,
            ImageSampleField.width < 20,
            NOT(
                ImageSampleField.tags.contains("dog")
            ),
        ),
    )

    # Combine sample and annotation filters, use logical `OR` inside annotation filter
    expr = AND(
        ImageSampleField.tags.contains("reviewed"),
        ObjectDetectionQuery(
            ObjectDetectionField.class_name == "car",
            OR(ObjectDetectionField.width >= 80, ObjectDetectionField.height >= 80)
        ),
    )

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```

=== "`order_by`"

    Setting the sorting of a query can be done by
    ```py
    query.order_by(<expression>)
    ```

    The order expression can be defined by
    `OrderByField(ImageSampleField.<field_name>).<order_direction>()` for sample fields or
    `OrderByEvaluationMetricField("<run_name>", "<metric_name>").<order_direction>()` for
    evaluation metrics.


    ```py
    from lightly_studio.core.dataset_query import (
        ImageSampleField,
        OrderByEvaluationMetricField,
        OrderByField,
    )

    # Sort the query by the width of the image in ascending order
    expr = OrderByField(ImageSampleField.width)
    expr = OrderByField(ImageSampleField.width).asc()

    # Sort the query by the file name in descending order
    expr = OrderByField(ImageSampleField.file_name).desc()

    # Sort the query by an evaluation metric in descending order
    expr = OrderByEvaluationMetricField("run1", "score").desc()

    # Assign any of the previous expressions to a query:
    query.order_by(expr)
    ```

=== "`slice`"

    Setting the slicing of a query can be done by:
    ```py
    query.slice(<offset>, <limit>)
    # OR
    query[<offset>:<stop>]
    ```

    ```py
    # Slice 2:5
    query.slice(offset=2, limit=3)
    query[2:5]

    # Slice :5
    query.slice(limit=5)
    query[:5]

    # Slice 5:
    query.slice(offset=5)
    query[5:]
    ```

For more details, see the [API reference](../api/dataset_query.md#datasetquery) of `DatasetQuery`.
