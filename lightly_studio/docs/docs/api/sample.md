# Sample

Each sample is a single data instance. The dataset stores references to all samples, allowing you to access, read, or update their attributes individually.

```py
import lightly_studio as ls

dataset = ls.ImageDataset.load_or_create(name="my_dataset")
dataset.add_images_from_path(path="path/to/images")

# Iterating over the data in the dataset
for sample in dataset:
    # Access sample attributes
    sample.sample_id        # Sample ID (UUID)
    sample.file_name        # Image file name (str), e.g. "img1.png"
    sample.file_path_abs    # Full image file path (str), e.g. "full/path/img1.png"
    sample.tags             # The set of sample tags (set[str]), e.g. {"tag1", "tag2"}
    sample.metadata         # Dict-like access to custom metadata

    # Adding/removing tags
    sample.add_tag("needs_review")
    sample.remove_tag("needs_review")
```

To attach custom metadata to samples, see [Metadata in Python](../concepts_and_tools/metadata.md#metadata-in-python).

## Sample

::: lightly_studio.core.sample
    options:
        members: [Sample]

## ImageSample

::: lightly_studio.core.image.image_sample
    options:
        members: [ImageSample]

## VideoSample

::: lightly_studio.core.video.video_sample
    options:
        members: [VideoSample]
