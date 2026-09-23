# Lightly Query Language

This document explains how to write queries in the
[LightlyStudio query editor.](search_and_filter.md#query-in-gui)

A query helps you find images that match certain rules. For example, you can search for:

- large images
- images with a specific file name
- tagged images
- images with a certain annotation, such as a classification, bounding box, or segmentation mask
- a logical combination of the above, using AND/OR/NOT operators.

## Query examples

The query language is quite simple and resembles WHERE clauses in SQL. We recommend learning it from examples.

```mysql
# Images that are at least 640 pixels wide or 400 pixels tall
width >= 640 OR height >= 400

# Images which do not have the tag "reviewed"
NOT "reviewed" IN tags

# Images with a "car" segmentation mask that is less than 100 pixels wide
segmentation_mask(class_name = "car" AND width < 100)
```

## Supported image fields

These fields can be used directly in a query:

- `width`
- `height`
- `file_name`
- `file_path_abs`
- `created_at`

Example queries:

```mysql
height >= 400
width >= 640
file_name = "cat.jpg"
file_path_abs != "/datasets/archive/bad.jpg"
created_at >= "2025-01-01T00:00:00Z"
```


## Tag filtering

Filtering for tags can be done using `"foo" IN tags`, which matches each image that has the tag `foo`:

```mysql
"car" IN tags
```

You can combine this with other criteria:
```mysql
"car" IN tags OR (height >= 400 AND width >= 640)
```

Other examples:
```mysql
"training" IN tags
NOT "rejected" IN tags
"training" IN tags OR "validation" IN tags
```


## Annotation match functions

An annotation is a classification, bounding box, or segmentation mask attached to an image.

The query language supports three annotation functions:

- `classification(...)`
- `object_detection(...)`
- `segmentation_mask(...)`

Each function contains another query inside the parentheses and matches an image when it has at least one annotation of that type that satisfies the nested query.

### Classification queries

Use `classification(...)` when you want to match image-level classifications. Example queries:

```mysql
classification(class_name = "cat")
classification(class_name != "background")
```

### Object detection queries

Use `object_detection(...)` when you want to match bounding boxes. The following fields are supported:

- `class_name`
- `x`
- `y`
- `width`
- `height`

Example queries:

```mysql
object_detection(x >= 10 AND y < 200)
object_detection(class_name = "cat" AND width >= 50 AND height >= 40)
object_detection(class_name = "cat" OR class_name = "dog")
object_detection(class_name != "background")
```

### Segmentation mask queries

Use `segmentation_mask(...)` when you want to match segmentation annotations.

It is part of the query grammar, uses the same boolean operators as `object_detection(...)`, and supports these fields:

- `class_name`
- `x`
- `y`
- `width`
- `height`

Example queries:

```mysql
segmentation_mask(class_name = "cat")
segmentation_mask(x != 0)
segmentation_mask(width > 80)
segmentation_mask(class_name = "cat" AND width >= 50 AND height >= 40)
```

## Combining top-level and annotation expressions

You can combine image properties with annotation queries:

```mysql
height > 400 AND object_detection(class_name = "cat")
width >= 640 AND classification(class_name = "approved")
"reviewed" IN tags AND segmentation_mask(class_name = "road")
```

## Complex examples

```mysql
# Large reviewed sample with a matching object detection
height > 400 AND width >= 640
AND "reviewed" IN tags
AND object_detection(class_name = "cat" AND width > 80 AND height > 80)

# Nested query with grouped sample filters and segmentation constraints
(file_path_abs != "/datasets/archive/bad.jpg" AND created_at >= "2025-01-01T00:00:00Z")
AND ("training" IN tags OR "validation" IN tags)
AND segmentation_mask(
    (class_name = "car" OR class_name = "truck")
    AND width >= 100
    AND height >= 60
    AND NOT (x < 10 OR y < 10)
)

# Nested query combining multiple annotation functions
"reviewed" IN tags
AND classification(class_name = "urban-scene")
AND (
    object_detection(class_name = "person" AND height >= 120)
    OR segmentation_mask(class_name = "road" AND width > 300)
)
```

## Grammar Notes

### Operator precedence

Operators are evaluated in this order:

1. `NOT`
2. `AND`
3. `OR`

Use parentheses whenever you want to make grouping explicit.

### Strings and comments

Strings can use double quotes or single quotes:

```mysql
file_name = "frame-0001.jpg"
file_name = 'frame-0001.jpg'
```

Comments start with `#` and continue to the end of the line:

```mysql
height >= 400 # keep only large images
```

### Keyword casing

The boolean and membership operators are case-insensitive. For example, `AND`, `OR`, `NOT`, and `IN` can also be written in lowercase.

### Miscellaneous

- `created_at` must be a valid datetime string that JavaScript `Date` can parse.
- `x`, `y` are valid inside `object_detection(...)` and `segmentation_mask(...)`, but not as top-level image fields.
