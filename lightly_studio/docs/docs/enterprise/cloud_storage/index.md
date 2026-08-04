# Cloud Storage

LightlyStudio Enterprise lets admins configure cloud storage credentials centrally.
Once set up, every Python client that calls `ls.connect()` receives the credentials
automatically, no per-user setup is needed. Cloud storage is read-only, LightlyStudio
will not write any data to your buckets or need write permissions.

Currently supported: **AWS S3** and **Google Cloud Storage (GCS)**. Azure support
is planned.

## How It Works

1. **Admin creates cloud provider credentials** with read access to the storage bucket.
   See [AWS S3 Setup](aws.md) or [Google Cloud Storage Setup](gcs.md) for a
   step-by-step guide.
2. **Admin saves the credentials** in the LightlyStudio Enterprise GUI.
3. **Python clients call `ls.connect()`** and receive the credentials automatically.

## Step 1: Get Your Cloud Credentials

Follow the guide for your cloud provider to create credentials with the required permissions:

- [AWS S3](aws.md)
- [Google Cloud Storage](gcs.md)

## Step 2: Add Credentials in the GUI

1. Open your LightlyStudio Enterprise instance in the browser.
2. Go to the **Datasets** page and click the **Cloud Storage Credentials** button.
   This button is only visible to admins.
3. Select your provider.
4. For Amazon S3, enter the **Access Key ID** and **Secret Access Key**. For
   Google Cloud Storage, paste the complete service-account JSON object.
5. Click **Save Credentials**.

The credentials are now stored on the server and shared with all Python client connections.
Saving replacement credentials also refreshes the active server configuration. Existing Python
clients should call `ls.connect()` again to receive rotated credentials.

## Step 3: Use Cloud Storage from Python

If you have not set up Python access yet, start with
[Connect from Python](../connect.md). After calling `ls.connect()`, cloud credentials are
injected into your local environment automatically, so you can use remote paths directly
without any extra client-side setup.

```python title="enterprise_cloud_storage.py"
import lightly_studio as ls

ls.connect()

dataset = ls.ImageDataset.load_or_create(name="s3_dataset")
dataset.add_images_from_path(path="s3://my-bucket/images/")
```

For Google Cloud Storage, use a `gcs://` path:

```python title="enterprise_gcs_storage.py"
import lightly_studio as ls

ls.connect()

dataset = ls.ImageDataset.load_or_create(name="gcs_dataset")
dataset.add_images_from_path(path="gcs://my-bucket/images/")
```

!!! note
    The Python client must have the cloud storage dependencies installed:
    ```shell
    pip install "lightly-studio[cloud-storage]"
    ```
    See [Using Cloud Storage](../../dataset_setup/cloud_storage.md) for more details on
    supported cloud operations.
