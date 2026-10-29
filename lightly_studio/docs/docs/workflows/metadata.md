# Metadata

Metadata allows you to store arbitrary key-value data for every sample in your dataset. It can be viewed and filtered in the GUI or managed through the Python API. Use metadata to attach context such as:

- capture conditions (e.g. weather, lighting, camera settings),
- GPS coordinates or location information,
- camera or sensor identifiers,
- production line or machine IDs,
- data source or collection campaign,
- recording date, season, or time of day,
- customer, project, or site identifiers,
- or any custom attribute you want to track.

For embeddings, [captions](captions.md), [annotations](annotations.md), [predictions](annotations.md), or [tags](tags.md), the corresponding built-in concepts are better suited.

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

### Add metadata to many samples

Use
[Dataset.update_metadata](../api/dataset.md#lightly_studio.core.dataset.Dataset.update_metadata)
to write metadata for many samples in a single call. It takes a list of
`(sample_id, metadata)` tuples:

```python
dataset.update_metadata([
    (sample_id_1, {"weather": "sunny", "temperature": 28}),
    (sample_id_2, {"weather": "rainy", "temperature": 15}),
])
```

!!! tip "Use the bulk call for many samples"
    Do not set `sample.metadata[key] = value` in a loop over thousands of samples. Each
    assignment is a separate database write, so 9 keys on 5,000 images take minutes.
    `dataset.update_metadata` writes the same values in seconds.

Metadata from an external source is usually keyed by file name. Build a
`file_name -> sample_id` mapping once, then make a single bulk call. The two examples below
do this for a Python dictionary (e.g. loaded from JSON) and for a CSV file.

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

### Look up a sample by file name

To get one sample by its file name, use
[ImageDataset.get_sample_by_file_name](../api/dataset.md#lightly_studio.ImageDataset.get_sample_by_file_name).
The file name must match `sample.file_name` exactly:

```python
sample = dataset.get_sample_by_file_name("img_001.jpg")
sample.metadata["weather"] = "sunny"
```

Each call runs one database query. To look up many samples, build the `file_name -> sample_id`
mapping shown above.

### Metadata on individual samples

Access and modify metadata on a `Sample` object using the `metadata` property, which behaves like a
dictionary. This is useful to read metadata or to change a few samples. To write metadata for many
samples, use the [bulk call](#add-metadata-to-many-samples).

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

    total = sum(channel_sums) or 1  # avoid divide-by-zero on fully black images
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

### Filter samples by metadata

Use `ImageSampleField.metadata["<path>"]` in a dataset query to select images by metadata values:

```python
from lightly_studio.core.dataset_query import AND, ImageSampleField

query = dataset.match(
    AND(
        ImageSampleField.metadata["location"] == "city",
        ImageSampleField.metadata["temperature"] >= 25,
    )
)
samples = query.to_list()
```

For video datasets, use `VideoSampleField.metadata` instead of `ImageSampleField.metadata`.

Filters support string and boolean equality, numeric comparisons, and nested paths such as
`extra.camera` or `keywords[0]`. Missing values and values of a different JSON type do not
match, including with `!=`. See [Metadata queries](search_and_filter.md#metadata-queries) for
the supported operators, path syntax, and comparison rules.
