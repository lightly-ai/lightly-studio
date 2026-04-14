# Metadata

Metadata allows you to store arbitrary key-value data for every sample in your dataset. Use it to
attach context such as capture conditions, GPS coordinates, model confidence scores, or any custom
attribute you want to track. Metadata can be viewed and filtered in the GUI or managed through the
Python API.

## View and Filter by Metadata in the GUI

In the main grid view, numeric metadata fields appear as range sliders in the left sidebar,
alongside the built-in dimension filters. To filter by metadata values, drag the slider handles
to narrow the visible samples to the desired range.

In the sample detail view, all metadata key-value pairs are listed in the side panel.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/metadata.mp4" type="video/mp4">
</video>

## Metadata in Python

### Metadata on individual samples

Access and modify metadata on a `Sample` object using the `metadata` property, which behaves like a
dictionary:

```python
# Assuming `dataset` is a lightly_studio dataset object
dataset = ...

for sample in dataset:
    # Read metadata. Returns None for missing keys.
    print(sample.metadata["temperature"])

    # Set a single value
    sample.metadata["temperature"] = 25.3
    sample.metadata["location"] = "city"
    sample.metadata["is_processed"] = True
    sample.metadata["keywords"] = ["outdoor", "daytime"]
    sample.metadata["extra"] = {"camera": "Canon", "lens": "50mm"}

    # Update multiple key-value pairs at once
    sample.metadata.update({"confidence": 0.95, "priority": 3})
```

Supported value types are `string`, `integer`, `float`, `boolean`, `list`, and `dict`.
Once a key is set with a given type, it is expected that values for other samples for that key use the same type.

### Bulk metadata updates

For larger datasets, setting metadata one sample at a time can be slow. Use
[Dataset.update_metadata](../api/dataset.md#lightly_studio.core.dataset.Dataset.update_metadata)
to update many samples in a single call. New keys are created on demand, and existing keys are
merged with the incoming values.

```python
import lightly_studio as ls

dataset = ls.ImageDataset.load()

sample_metadata = [
    (sample.sample_id, {"weather": "sunny", "temperature": 28})
    for sample in dataset
]
dataset.update_metadata(sample_metadata)
```
