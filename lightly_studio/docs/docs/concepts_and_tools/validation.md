# Annotation Validation

LightlyStudio imports object-detection annotations from COCO, YOLO, Pascal VOC, and labelformat.
A bad export can add boxes with a wrong size or position. Use `dataset.validate()` to check the
annotations for integrity problems and get a report.

## Validate in Python

Call `validate()` with the annotation source to check. It returns a
[`ValidationReport`](../api/validation.md#validationreport).

```python
report = dataset.validate(annotation_source="predictions")

for issue in report.degenerate_boxes:
    print("zero or negative size:", issue.sample_id, issue.annotation_id)
for issue in report.out_of_bounds_boxes:
    print("outside the image:", issue.sample_id, issue.annotation_id)
```

It reports these problems:

- a non-positive width or height (`degenerate_boxes`)
- a box that extends past the image bounds (`out_of_bounds_boxes`)

Each issue gives the image `sample_id` and the flagged `annotation_id`. Pass a
[`DatasetQuery`](../api/dataset_query.md) to check only a subset of the samples.

See the [Annotation Validation API Reference](../api/validation.md) for the full API surface.
