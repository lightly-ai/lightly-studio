# Search and Filter

Search helps you find visually or semantically similar samples from a text or image. Filters narrow down the samples currently shown in the view by tags, labels, dimensions, and other numeric metadata.
Use the GUI for similarity search and quick filtering, and use DatasetQuery in Python when you need reusable filtering, sorting, and slicing in code.


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

## Filter in GUI

The left sidebar combines the most common ways to narrow down the visible samples:

- `Tags`: Click one or more tags to focus on the subset you care about, such as `labeled` or `unlabeled`.
- `Labels`: Click one or more labels to show items with those annotations.
- `Dimensions`: Use `Width` and `Height` to constrain the visible item size.
- `Metadata`: If numeric metadata fields are available, they appear as additional sliders in the same area.

![Tag filters](https://storage.googleapis.com/lightly-public/studio/search_filter_tags_v3.png){ width="100%"}


For videos, the sidebar adds `Duration`. If the videos in the current view contain varying frame rates, it also shows `FPS`.

![Video filters](https://storage.googleapis.com/lightly-public/studio/search_filter_videos_v4.jpg){ width="100%" }


## Dataset Query in Python

You can programmatically filter samples by attributes (e.g., image size, tags), sort them, and select subsets. This is useful for creating training/validation splits, finding specific samples, or exporting filtered data.


```py
from lightly_studio.core.dataset_query import AND, OR, NOT, OrderByField, ImageSampleField

# QUERY: Define a lazy query, composed by: match, order_by, slice
# match: Find all samples that need labeling plus small samples (< 500px) that haven't been reviewed.
query = dataset.match(
    OR(
        AND(
            ImageSampleField.width < 500,
            NOT(ImageSampleField.tags.contains("reviewed"))
        ),
        ImageSampleField.tags.contains("needs-labeling")
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

```

For video, use `VideoSampleField` instead. For example, the following code works for video.
```py
from lightly_studio.core.dataset_query import AND, OR, NOT, OrderByField, VideoSampleField

# QUERY: Define a lazy query, composed by: match, order_by, slice
# match: Find all samples that need labeling plus small samples (< 500px) that have small FPS.
query = dataset.match(
    OR(
        AND(
            VideoSampleField.width < 500,
            NOT(VideoSampleField.fps >= 30)
        ),
        VideoSampleField.tags.contains("needs-labeling")
    )
)

# order_by: Sort the samples by their width descending.
query.order_by(
    OrderByField(VideoSampleField.width).desc()
)
```

### Reference

=== "`match`"

    You can define query filters with:
    ```py
    query.match(<expression>)
    ```
    To create an expression for filtering on certain sample fields, the `ImageSampleField.<field_name> <operator> <value>` syntax can be used. Available field names can be seen in [`ImageSampleField`](/api/core/#lightly_studio.core.dataset_query.image_sample_field.ImageSampleField).

    <details>
    <summary>Examples:</summary>

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

    </details>

    The filtering on individual fields can flexibly be combined to create more complex match expression. For this, the boolean operators [`AND`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.AND), [`OR`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.OR), and [`NOT`](/api/core/#lightly_studio.core.dataset_query.boolean_expression.NOT) are available. Boolean operators can arbitrarily be nested.

    <details>
    <summary>Examples:</summary>

    ```py
    from lightly_studio.core.dataset_query import AND, OR, NOT, ImageSampleField

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

    # Assign any of the previous expressions to a query:
    query.match(expr)
    ```
    </details>

=== "`order_by`"

    Setting the sorting of a query can be done by
    ```py
    query.order_by(<expression>)
    ```

    The order expression can be defined by `OrderByField(ImageSampleField.<field_name>).<order_direction>()`.

    <details>
    <summary>Examples:</summary>

    ```py
    from lightly_studio.core.dataset_query import OrderByField, ImageSampleField

    # Sort the query by the width of the image in ascending order
    expr = OrderByField(ImageSampleField.width)
    expr = OrderByField(ImageSampleField.width).asc()

    # Sort the query by the file name in descending order
    expr = OrderByField(ImageSampleField.file_name).desc()

    # Assign any of the previous expressions to a query:
    query.order_by(expr)
    ```
    </details>

=== "`slice`"

    Setting the slicing of a query can be done by:
    ```py
    query.slice(<offset>, <limit>)
    # OR
    query[<offset>:<stop>]
    ```

    <details>
    <summary>Examples:</summary>

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
    </details>

For more details, see the [API reference](../api/dataset_query.md#datasetquery) of `DatasetQuery`.
