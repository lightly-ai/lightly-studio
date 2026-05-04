# Lightly Query Language

This document explains how to write queries in the Studio query editor.

A query helps you find images that match certain rules. For example, you can search for:

- large images
- images with a specific file name
- tagged images
- images with a certain annotation, such as a classification, bounding box, or segmentation mask
- a logical combination of the above, using AND/OR/NOT operators.

## Query examples

An example of a query filtering images that are taller than 400 pixels and at least 640 pixels wide.

```sql
height >= 400 AND width >= 640
```

If we subsitute `AND` for `OR`, an image is filtered if either of these conditions is true.

### Nesting with parentheses

You can create more complex queries by nesting sub-queries in parethesis. If we want either an image that is large or its file name is `cover.jpg`, we use:

```sql
(height >= 400 AND width >= 640) OR file_name == "cover.jpg"
```

### Negation

We also support the logical `NOT` operator, the following example filters images that are not large:

```sql
NOT (height >= 400 AND width >= 640)
```

### Tag filtering

Filtering for tags can be the done using `"foo" IN tags` which matches each image containing `foo` as a tag:

```sql
(height >= 400 AND width >= 640) OR "car" IN tags
```

Other examples:
```sql
"training" IN tags
NOT "rejected" IN tags
"training" IN tags OR "validation" IN tags
```


### Supported image fields

These fields can be used directly in a query:

- `width`
- `height`
- `file_name`
- `file_path_abs`
- `created_at`

Example queries:

```sql
height >= 400
width >= 640
file_name == "cat.jpg"
file_path_abs != "/datasets/archive/bad.jpg"
created_at >= "2025-01-01T00:00:00Z"
```


## Annotation match functions

Annotations are labels or shapes attached to an image.

The query language supports three annotation functions:

- `classification(...)`
- `object_detection(...)`
- `segmentation_mask(...)`

Each function contains another query inside the parentheses.

## Classification queries

Use `classification(...)` when you want to match image-level labels. Examples:

```sql
classification(label == "cat")
classification(label != "background")
```

## Object detection queries

Use `object_detection(...)` when you want to match bounding boxes. The following fields are supported:

- `label`
- `x`
- `y`
- `width`
- `height`

Example queries:

```sql
object_detection(label == "cat")
object_detection(x >= 10 AND y < 200)
object_detection(label == "cat" AND width >= 50 AND height >= 40)
object_detection(label == "cat" OR label == "dog")
object_detection(label != "background")
```

## Segmentation mask queries

Use `segmentation_mask(...)` when you want to match segmentation annotations.

It currently supports the same queryable fields as object detection, but it is intentionally its own function:

- `label`
- `x`
- `y`
- `width`
- `height`

### Examples

```sql
segmentation_mask(label == "cat")
segmentation_mask(x != 0)
segmentation_mask(width > 80)
segmentation_mask(label == "cat" AND width >= 50 AND height >= 40)
```

## Combining top-level and annotation expressions

You can combine image properties with annotation queries:

```sql
height > 400 AND object_detection(label == "cat")
width >= 640 AND classification(label == "approved")
"reviewed" IN tags AND segmentation_mask(label == "road")
```

## Complex examples

### Large reviewed sample with a matching object detection

```sql
height > 400
AND width >= 640
AND "reviewed" IN tags
AND object_detection(label == "cat" AND width > 80 AND height > 80)
```

### Nested query with grouped sample filters and object detection constraints

```sql
(file_path_abs != "/datasets/archive/bad.jpg" AND created_at >= "2025-01-01T00:00:00Z")
AND ("training" IN tags OR "validation" IN tags)
AND object_detection((label == "cat" OR label == "dog") AND NOT (x < 5 OR y < 5))
```

### Nested query mixing top-level logic with segmentation constraints

```sql
(
    (height > 720 AND width > 1280)
    OR ("priority" IN tags AND NOT "rejected" IN tags)
)
AND segmentation_mask(
    (label == "car" OR label == "truck")
    AND width >= 100
    AND height >= 60
    AND NOT (x < 10 OR y < 10)
)
```

### Nested query combining multiple annotation functions

```sql
"reviewed" IN tags
AND classification(label == "urban-scene")
AND (
    object_detection(label == "person" AND height >= 120)
    OR segmentation_mask(label == "road" AND width > 300)
)
```

## Strings and comments

Strings can use double quotes or single quotes:

```sql
file_name == "frame-0001.jpg"
file_name == 'frame-0001.jpg'
```

## Notes

- `created_at` must be a valid datetime string that JavaScript `Date` can parse.
- `x`, `y` are valid inside `object_detection(...)` and `segmentation_mask(...)`, but not as top-level image fields.
