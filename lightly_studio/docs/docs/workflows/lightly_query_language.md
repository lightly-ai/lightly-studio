# Lightly Query Language

This document explains how to write queries in the
[LightlyStudio query editor.](search_and_filter.md#query-in-gui)

A query helps you find images or videos that match certain rules. For example, you can search for:

- large images
- videos with a specific frame rate or duration
- images with a specific file name
- tagged images
- images with specific metadata values
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

## Supported video fields

In a video collection, enter field names directly in the query editor.

| Field | Meaning |
| --- | --- |
| `fps` | Frame rate in frames per second |
| `duration_s` | Video duration in seconds |
| `width`, `height` | Video frame dimensions in pixels |
| `file_name` | Video file name |
| `file_path_abs` | Absolute path to the video file |

```mysql
# Videos recorded at 29.97 frames per second or higher
fps >= 29.97

# Videos longer than 10 seconds with a frame rate of 30 FPS
duration_s > 10 AND fps = 30
```

## Video frame queries

Use `frame(...)` to return videos with a matching frame. Inside it, combine annotation
functions with `frame_timestamp_s`, the frame’s presentation timestamp in seconds on the video’s
timeline. The first frame might have a nonzero timestamp. If the timestamp is unavailable,
LightlyStudio stores `-1.0`, so `frame_timestamp_s < 5` also matches frames with an unknown time.

```mysql
# A person appears on a frame with a timestamp from 0 up to (but excluding) 5 seconds
frame(object_detection(class_name = "person") AND frame_timestamp_s >= 0 AND frame_timestamp_s < 5)

# A person and a car appear on the same frame
frame(object_detection(class_name = "person") AND object_detection(class_name = "car"))

# Both appear in the video, possibly on different frames
frame(object_detection(class_name = "person")) AND frame(object_detection(class_name = "car"))
```

`frame(NOT object_detection(class_name = "car"))` requires at least one frame without a car detection.
`NOT frame(object_detection(class_name = "car"))` matches videos with no car detections on any frame, including videos with no frames.

## Video event queries

Use `event(...)` to return videos with at least one temporal event that satisfies the expression.
Only classifications attached to a video can have a time span when you create them.
You can filter by annotation class (`class_name`), annotation source (`source`), `confidence`,
and event boundaries (`start_time_s` and `end_time_s`, in seconds from the start of the video).

```mysql
# A run event starts before five seconds
event(class_name = "run" AND start_time_s < 5)

# A run event and a walk event both occur in the video
event(class_name = "run") AND event(class_name = "walk")
```

On the Videos page, `classification(class_name = "run")` matches both whole-video classifications
and temporal events. Use `event(class_name = "run")` to find only temporal events.

## Metadata filtering

Use `metadata["path"]` to compare sample metadata. Quote the path with double or single quotes.
Use dots for nested fields and zero-based array indices in brackets:

```mysql
metadata["camera"] = "front"
metadata["reviewed"] = true
metadata["quality_score"] >= 0.8
metadata["odometry.acc[1]"] < -0.2
width >= 640 AND metadata["quality_score"] >= 0.8
```

Numbers support `=`, `!=`, `<`, `<=`, `>`, and `>=`. Strings and booleans support only `=` and `!=`. Boolean literals are case-insensitive, so `true` and `TRUE` mean the same thing.

Metadata comparisons work on image and video samples. They are not supported inside annotation
match functions. Metadata `IN (...)` and comparisons with `null` are not yet supported.

### Missing values and negation

A metadata comparison does not match a missing path, null, or a value of another type.
This also applies to `!=`:

```mysql
# Matches string camera values other than "front"; excludes missing, null, and other types
metadata["camera"] != "front"

# Matches everything except the string camera value "front"; includes missing, null, and other types
NOT metadata["camera"] = "front"
```

`NOT` negates the entire comparison, including whether a compatible metadata value exists.

The editor suggests a `metadata["path"]` snippet in sample expressions and `true`/`false` after
metadata `=` or `!=`. Hover over `metadata` for syntax and comparison help. Enter a path from
your dataset; completion does not list dataset metadata keys.

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

Use these functions to match classifications, bounding boxes, and segmentation masks:

- `classification(...)`
- `object_detection(...)`
- `segmentation_mask(...)`

Each function matches when at least one annotation of that type satisfies the expression inside the parentheses.

Bounding boxes and segmentation masks belong to images or individual video frames.
In an image query, use `object_detection(...)` or `segmentation_mask(...)` directly.
In a video query, wrap either function in `frame(...)` to find videos with a matching frame.
For example, `frame(segmentation_mask(class_name = "cat"))` finds videos with a cat mask on at least one frame.

### Classification queries

Use `classification(...)` to match image and video classifications, including temporal events. To filter by
event start or end time, see [Video event queries](#video-event-queries). Example queries:

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

## Sample evaluation filtering

Use `sample_evaluation(...)` to filter samples by metrics from a named evaluation run:

```mysql
sample_evaluation(name = "eval-tagged-samples" AND "tp" >= 1 AND "fn" >= 5 AND "fp" = 0)
sample_evaluation(name = "eval-tagged-samples" AND ("tp" > 0 OR "fn" > 0) AND NOT "fp" > 2)
sample_evaluation(name = "eval-tagged-samples" AND "custom-score" < -0.5)
```

Start with `name = "run-name"`, then optionally add `AND` followed by metric criteria.
A name-only query matches all samples evaluated by that run. Metric criteria support
parentheses, `NOT`, `AND`, and `OR` (in that precedence order), and numeric comparisons
with `=`, `!=`, `<`, `<=`, `>`, and `>=`.

All metric names require single or double quotes, including the built-in keywords
`"tp"`, `"fp"`, `"fn"`, `"disagreement"`, and `"miou"`. Custom metric names are also
quoted, such as `"custom_score"`.
Metric thresholds must be finite numbers, including decimals.

Missing metrics do not match comparisons, including `!=`. An inner `NOT` can match a
missing metric, but still requires the sample to belong to the selected run. An outer
`NOT sample_evaluation(...)` also matches samples outside that run.

Combine evaluation functions with other sample conditions or separate evaluation functions
using `AND`, `OR`, and `NOT`. Evaluation functions cannot be nested inside annotation functions.


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
