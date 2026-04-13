# Metadata

Metadata stores arbitrary key-value information on each sample in your dataset. Use metadata to
attach context such as capture conditions, GPS coordinates, model confidence scores, or any custom
attribute you want to track. Metadata can be viewed and filtered in the GUI or managed through the
Python API.

## View and Filter by Metadata in the GUI

All sample metadata key-value pairs are listed in the side panel in the sample detail view.

In the main grid view, numeric metadata fields appear as range sliders in the left sidebar,
alongside the built-in dimension filters. To filter by metadata values, drag the slider handles
to narrow the visible samples to the desired range.

<video autoplay loop muted playsinline controls style="width: 100%;">
  <source src="https://storage.googleapis.com/lightly-public/studio/metadata.mp4" type="video/mp4">
</video>

## Metadata in Python

Supported value types are `string`, `integer`, `float`, `boolean`, `list`, `dict`, and
`GPSCoordinate`. Once a key is set with a given type, subsequent values for that key must use the
same type.

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
    sample.metadata["temperature"] = 25
    sample.metadata["location"] = "city"
    sample.metadata["is_processed"] = True

    # Update multiple key-value pairs at once
    sample.metadata.update({"confidence": 0.95, "priority": 3})
```

### GPS coordinates

The `GPSCoordinate` helper stores a latitude/longitude pair and is automatically serialized to a
nested dictionary with `lat` and `lon` fields:

```python
from lightly_studio.metadata.gps_coordinate import GPSCoordinate

sample.metadata["gps_coordinates"] = GPSCoordinate(lat=40.7128, lon=-74.0060)
```

### Bulk metadata updates

For larger datasets, setting metadata one sample at a time is slow. Use `Dataset.update_metadata`
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

### Computed metadata

Lightly Studio can compute metadata values from embeddings and store them back on each sample.
The resulting numeric fields can then be used as filters in the GUI or for sorting via
`DatasetQuery`.

```python
# Typicality: how typical each sample is compared to its nearest neighbors.
dataset.compute_typicality_metadata(metadata_name="typicality")

# Similarity: how similar each sample is to the samples in a given tag.
dataset.compute_similarity_metadata(
    query_tag_name="reference",
    metadata_name="similarity_to_reference",
)
```
