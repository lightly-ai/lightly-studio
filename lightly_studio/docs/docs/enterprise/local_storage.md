# Local Storage

This guide explains how to use local disk or NAS/shared storage with
LightlyStudio Enterprise in an on-premise deployment.

It is intended for admins who connect from Python via `ls.connect()` and then
index datasets from storage that stays under their own control.

Local storage is supported only for on-premise deployments. It does not
work for the Lightly-hosted deployment. If you use Lightly-hosted, use
[Cloud Storage](cloud_storage/index.md) instead.

## How It Works

When you call `ls.connect()`, LightlyStudio stores file references in the
shared PostgreSQL database. It does **not** upload files into LightlyStudio,
copy them into the container, or rewrite their paths. It reads raw images and videos
directly from your storage when the GUI needs them. The database stores metadata and
file paths, not the raw media itself.

This means the path used by your Python script must also be valid for the
`studio` container that later serves the files to the GUI.

!!! warning "Same Path Required"
    The same absolute path must work in both places:

    1. In the Python process that indexes the data
    2. On the Docker host running the on-premise deployment

    If these paths differ, indexing can appear to work, but the LightlyStudio GUI
    will later fail to open the files.

## Step 1: Choose a Shared Absolute Path

Pick one absolute path that will be used consistently across the deployment.
This can point to:

- a local directory on the Docker host
- a NAS or other shared storage mount

Examples:

- `/mnt/datasets`
- `/srv/lightly/datasets`

Relative paths are a bad fit for this workflow. Use absolute paths only.

## Step 2: Set `DATASET_PATH`

Set `DATASET_PATH` in your deployment environment `.env` file to the absolute storage
root you want to expose to LightlyStudio.

Mounting a top-level path is fine. Your Python scripts can later index specific
subdirectories below that root as separate datasets.

For example, you can set `DATASET_PATH=/mnt/datasets` and then index
`/mnt/datasets/dataset_a/images` and `/mnt/datasets/dataset_b/images` as
different datasets.

It is also fine to broaden the mounted root later, for example from
`/mnt/datasets/dataset_a` to `/mnt/datasets`, as long as the absolute paths
stored for already indexed files remain valid.

## Step 3: Make the Same Path Available to Python

Run your Python indexing script in an environment that can access the same
storage root at the same absolute path you set in `DATASET_PATH`.

This works out of the box when Python runs:

- on the same machine as the Docker host
- on another machine that mounts the same shared storage at the same absolute
  path

If Python runs on a different machine where the storage is mounted at a
different absolute path (for example, `DATASET_PATH=/mnt/datasets` on the
Docker host, but the NAS is mounted at `/home/alice/datasets` on the Python
machine), create a symlink on the Python machine so that `DATASET_PATH` also
resolves there:

```shell
sudo ln -s /home/alice/datasets /mnt/datasets
```

Then pass paths under `/mnt/datasets/...` to the dataset loading methods.

## Step 4: Connect from Python and Index Data

Start with [Connect from Python](connect.md). After `ls.connect()`, use
absolute paths under your chosen storage root.

=== "Raw Images"

    ```python
    import lightly_studio as ls

    ls.connect()

    dataset = ls.ImageDataset.load_or_create("local_images")
    dataset.add_images_from_path(path="/mnt/datasets/local_images/images")
    ```

=== "Raw Videos"

    ```python
    import lightly_studio as ls

    ls.connect()

    dataset = ls.VideoDataset.load_or_create("local_videos")
    dataset.add_videos_from_path(path="/mnt/datasets/local_videos/videos")
    ```

=== "COCO Import"

    ```python
    import lightly_studio as ls

    ls.connect()

    dataset = ls.ImageDataset.load_or_create("local_coco")
    dataset.add_samples_from_coco(
        annotations_json="/mnt/datasets/local_coco/instances_train.json",
        images_path="/mnt/datasets/local_coco/images",
        annotation_type=ls.AnnotationType.SEGMENTATION_MASK,
    )
    ```

## Troubleshooting

- If indexing succeeds but files do not open in the GUI, verify that the same
  absolute path works in Python, on the host, and inside the `studio`
  container. To check the expected path, go in the GUI on the details view of an image
  or view and check the Filepath shown there. 
- If you move or rename files after indexing them, the stored file references
  become invalid and the GUI can no longer load those files.
- If your Python script runs on another machine, mount the same local/NAS
  storage there using the same absolute path.
