# Metadata

Metadata allows you to store arbitrary key-value data for every sample in your dataset. Use it to
attach context such as capture conditions, GPS coordinates, model confidence scores, or any custom
attribute you want to track. Metadata can be viewed and filtered in the GUI or managed through the
Python API.

## View and Filter Metadata in the GUI

In the main grid view, numeric metadata fields appear as range sliders in the left sidebar,
alongside the built-in dimension filters. To filter by metadata values, drag the slider handles
to narrow the visible samples to the desired range.

In the sample detail view, all metadata key-value pairs are listed in the side panel.

!!! note
    Metadata in the GUI is read-only. To edit metadata, use the Python API described below.

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

### Add metadata from external sources

You can bulk add metadata from any external source by providing it as a dictionary or CSV file. Use
[Dataset.update_metadata](../api/dataset.md#lightly_studio.core.dataset.Dataset.update_metadata)
to write metadata for multiple samples in a single call. The two examples below show
how to do this given a python dictionary (e.g. loaded from JSON) or a CSV file.

=== "Python dict"

    ```python
    from typing import Any

    import lightly_studio as ls

    dataset = ls.ImageDataset.load()

    # Provided by you. Keys must exactly match sample.file_name.
    filename_to_metadata: dict[str, dict[str, Any]] = {
        "img_001.jpg": {"weather": "sunny", "temperature": 28},
        "img_002.jpg": {"weather": "rainy", "temperature": 15},
    }

    filename_to_sample_id = {sample.file_name: sample.sample_id for sample in dataset}

    sample_metadata = []
    for filename, metadata in filename_to_metadata.items():
        sample_id = filename_to_sample_id.get(filename)
        if sample_id is None:
            raise ValueError(
                f"File name {filename!r} not found in dataset. "
                f"Keys must match sample.file_name exactly."
            )
        sample_metadata.append((sample_id, metadata))

    dataset.update_metadata(sample_metadata)
    ```

=== "CSV"

    ```python
    import csv
    from typing import Any

    import lightly_studio as ls

    dataset = ls.ImageDataset.load()

    # CSV has columns: file_name,weather,temperature
    # file_name must match sample.file_name exactly.
    filename_to_metadata: dict[str, dict[str, Any]] = {}
    with open("metadata.csv") as f:
        for row in csv.DictReader(f):
            filename_to_metadata[row["file_name"]] = {
                "weather": row["weather"],
                "temperature": float(row["temperature"]),
            }

    filename_to_sample_id = {sample.file_name: sample.sample_id for sample in dataset}

    sample_metadata = []
    for filename, metadata in filename_to_metadata.items():
        sample_id = filename_to_sample_id.get(filename)
        if sample_id is None:
            raise ValueError(
                f"File name {filename!r} not found in dataset. "
                f"Keys must match sample.file_name exactly."
            )
        sample_metadata.append((sample_id, metadata))

    dataset.update_metadata(sample_metadata)
    ```

### Add metadata calculated from images

You can also iterate the dataset, open each image with PIL, compute derived statistics, and write
them back in a single bulk call. The example below computes the mean luminance and the per-channel
brightness ratio for every image.

```python
import lightly_studio as ls
import tqdm
from PIL import Image, ImageStat

dataset = ls.ImageDataset.load()

sample_metadata = []
for sample in tqdm.tqdm(dataset):
    with Image.open(sample.file_path_abs) as img:
        rgb = img.convert("RGB")
        channel_sums = ImageStat.Stat(rgb).sum  # [sum_R, sum_G, sum_B]
        luminance = ImageStat.Stat(rgb.convert("L")).mean[0]

    total = sum(channel_sums)
    sample_metadata.append(
        (
            sample.sample_id,
            {
                "luminance": luminance,
                "red_ratio": channel_sums[0] / total,
                "green_ratio": channel_sums[1] / total,
                "blue_ratio": channel_sums[2] / total,
            },
        )
    )

dataset.update_metadata(sample_metadata)
```

`dataset.update_metadata` merges values: new keys are created on demand, and existing keys are
overwritten by the incoming values. Metadata on other keys is left untouched.
