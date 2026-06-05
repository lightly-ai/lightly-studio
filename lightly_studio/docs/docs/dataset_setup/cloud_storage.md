# Cloud Storage

To load images or videos directly from a cloud storage provider (like AWS S3, GCS, etc.), first install the required dependencies:

```shell
pip install "lightly-studio[cloud-storage]"
```

This installs [s3fs](https://github.com/fsspec/s3fs) (for S3), [gcsfs](https://github.com/fsspec/gcsfs) (for GCS), and [adlfs](https://github.com/fsspec/adlfs) (for Azure). For other providers, see the [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#other-known-implementations).

**Example: Loading images from S3**

```py
import lightly_studio as ls

dataset = ls.ImageDataset.load_or_create(name="s3_dataset")
dataset.add_images_from_path(path="s3://my-bucket/images/")

ls.start_gui()
```

**Example: Loading videos from S3**

```py
import lightly_studio as ls

dataset = ls.VideoDataset.load_or_create(name="s3_video_dataset")
dataset.add_videos_from_path(path="s3://my-bucket/videos/")

ls.start_gui()
```

Files remain in the remote storage and are streamed to the UI on demand. Make sure your cloud credentials are configured for the selected provider.

**Current Limitations:**

!!! warning "Cloud Storage Limitation"
    Cloud storage is supported for raw media folders via `add_images_from_path()` and `add_videos_from_path()`, and for COCO object detection and segmentation mask imports via `add_samples_from_coco()`. Other dataset importers still expect local files.
