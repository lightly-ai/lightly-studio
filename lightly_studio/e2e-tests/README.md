# Cloud Storage E2E Tests

Three e2e scripts test remote cloud storage connectivity:

| Provider | Script | Makefile target |
|---|---|---|
| Amazon S3 | `e2e-tests/index_s3.py` | `make start-e2e-s3` |
| Google Cloud Storage | `e2e-tests/index_gcs.py` | `make start-e2e-gcs` |
| Azure Blob Storage | `e2e-tests/index_azure.py` | `make start-e2e-azure` |

---

## Amazon S3

The S3 e2e test indexes a dataset directly from a private S3 bucket using
standard AWS credentials.

### Prerequisites

- AWS CLI configured (`aws configure` or environment variables)
- An S3 bucket with the `coco_subset_128_images` dataset uploaded
- The `cloud-storage` extra installed

```shell
cd lightly_studio
uv sync --extra cloud-storage
```

### 1. Upload the Dataset

```shell
BUCKET="<your-bucket-name>"
PREFIX="coco_subset_128_images"
SOURCE_DIR="<absolute-path-to-coco_subset_128_images>"

aws s3 cp "$SOURCE_DIR/" "s3://$BUCKET/$PREFIX/" --recursive
```

### 2. Configure Credentials

Use any of the standard AWS credential mechanisms. The simplest is environment
variables:

```shell
export AWS_ACCESS_KEY_ID="<access-key-id>"
export AWS_SECRET_ACCESS_KEY="<secret-access-key>"
# For temporary credentials also set:
export AWS_SESSION_TOKEN="<session-token>"
export AWS_DEFAULT_REGION="<region>"   # e.g. us-east-1
```

Alternatively, `aws configure` writes `~/.aws/credentials` which is picked up
automatically.

### 3. Run the Test

Edit the bucket path in `e2e-tests/index_s3.py`:

```python
# Change this line to point at your bucket:
dataset.add_images_from_path(path="s3://<your-bucket>/coco_subset_128_images/", embed=False)
```

Then run:

```shell
make start-e2e-s3
# or, after the first build:
uv run e2e-tests/index_s3.py
```

The test should create the `s3_dataset` dataset, index 128 images, and start
LightlyStudio at <http://localhost:8001>.

### Troubleshooting

- `NoCredentialsError`: export `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
  in the same terminal.
- `AccessDenied`: the IAM principal needs `s3:GetObject` and `s3:ListBucket`
  on the target bucket and prefix.
- Missing `s3fs`: run `uv sync --extra cloud-storage`.

### Clean Up Credentials

```shell
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
```

Never commit AWS credentials.

---

## Google Cloud Storage

The GCS e2e test indexes a dataset directly from a private GCS bucket.

### Prerequisites

- `gcloud` CLI authenticated (`gcloud auth application-default login`)
- A GCS bucket with the `coco_subset_128_images` dataset uploaded
- The `cloud-storage` extra installed

```shell
cd lightly_studio
uv sync --extra cloud-storage
```

### 1. Upload the Dataset

```shell
BUCKET="<your-bucket-name>"
SOURCE_DIR="<absolute-path-to-coco_subset_128_images>"

gsutil -m cp -r "$SOURCE_DIR" "gs://$BUCKET/"
```

### 2. Configure Credentials

**Option A — Application Default Credentials (recommended for local dev):**

```shell
gcloud auth application-default login
```

This writes credentials to `~/.config/gcloud/application_default_credentials.json`,
which GCS clients pick up automatically via the `GOOGLE_APPLICATION_CREDENTIALS`
environment variable convention.

**Option B — Service account key file:**

```shell
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

**Option C — fsspec inline config:**

```shell
export FSSPEC_GCS='{"token": "/path/to/service-account-key.json"}'
```

### 3. Run the Test

The `index_gcs.py` script currently hard-codes a specific bucket path. Edit it
to point at your bucket before running:

```python
# index_gcs.py — change this line:
dataset.add_images_from_path(path="gs://<your-bucket>/coco_subset_128_images/", embed=False)
```

Then run:

```shell
make start-e2e-gcs
# or, after the first build:
uv run e2e-tests/index_gcs.py
```

The test should create the `gcs_dataset` dataset, index 128 images, and start
LightlyStudio at <http://localhost:8001>.

### Troubleshooting

- `DefaultCredentialsError`: run `gcloud auth application-default login` or set
  `GOOGLE_APPLICATION_CREDENTIALS`.
- `403 Forbidden`: the service account needs `storage.objects.get` and
  `storage.objects.list` on the bucket.
- Missing `gcsfs`: run `uv sync --extra cloud-storage`.

### Clean Up Credentials

```shell
unset GOOGLE_APPLICATION_CREDENTIALS FSSPEC_GCS
```

Never commit service-account key files.

---

## Azure Blob Storage

The Azure E2E test indexes the COCO example dataset directly from a private
Azure Blob Storage container. Use separate SAS tokens for uploading the test
data and for running LightlyStudio. LightlyStudio only needs read and list
permissions.

### Prerequisites

- [AzCopy](https://learn.microsoft.com/azure/storage/common/storage-use-azcopy-v10)
- An Azure Storage account with a private container named `test`
  (create via the [Azure portal](https://portal.azure.com) if it does not exist)
- The local `coco_subset_128_images` example dataset

Install the project dependencies, including Azure filesystem support:

```shell
cd lightly_studio
uv sync --extra cloud-storage
```

### 1. Configure the Test Resources

Set the storage account name and local dataset path:

```shell
ACCOUNT="<storage-account-name>"
CONTAINER="test"
SOURCE_DIR="<absolute-path-to-coco_subset_128_images>"
```

### 2. Upload the Dataset

Generate a short-lived SAS token with upload permissions (`racwdl`) from the
[Azure portal](https://portal.azure.com): navigate to the storage account →
**Containers** → `test` → **Generate SAS**, set the expiry to tomorrow, and
copy the **Blob SAS token** (starts with `sv=`).

```shell
UPLOAD_SAS="<paste-sas-token-here>"
UPLOAD_URL="https://${ACCOUNT}.blob.core.windows.net/${CONTAINER}?${UPLOAD_SAS}"

azcopy copy \
  "${SOURCE_DIR}/*" \
  "$UPLOAD_URL" \
  --recursive=true \
  --from-to=LocalBlob
```

The container must have this layout because `index_azure.py` uses these paths:

```text
test/
├── images/
│   ├── 000000565296.jpg
│   └── ...
└── instances_train2017.json
```

### 3. Configure Read-Only Credentials

Generate a separate SAS with only read and list permissions (`rl`) from the
[Azure portal](https://portal.azure.com): same path as above but tick only
**Read** and **List**, set expiry to a few days ahead, and copy the token.

```shell
READ_SAS="<paste-read-only-sas-token-here>"
READ_URL="https://${ACCOUNT}.blob.core.windows.net/${CONTAINER}?${READ_SAS}"

# Verify access before running the test:
azcopy list "$READ_URL"
```

Configure the fsspec credentials consumed by `index_azure.py`. Do not print the
value because it contains the SAS token.

```shell
export FSSPEC_ABFS="$(
  printf '{"account_name":"%s","sas_token":"%s"}' "$ACCOUNT" "$READ_SAS"
)"

printenv FSSPEC_ABFS >/dev/null \
  && echo "FSSPEC_ABFS is configured" \
  || echo "FSSPEC_ABFS is missing"
```

### 4. Run the Test

From the `lightly_studio` backend directory, build and start the Azure E2E
environment:

```shell
make start-e2e-azure
```

After the first build, use the following command for faster retries:

```shell
uv run e2e-tests/index_azure.py
```

The test should create the `azure_coco_dataset` dataset, index 128 images and
their instance-segmentation annotations, and start LightlyStudio at
<http://localhost:8001>. Embedding generation is disabled to keep the test
focused on Azure connectivity and remote indexing.

### Troubleshooting

- `Set FSSPEC_ABFS...`: export `FSSPEC_ABFS` in the same terminal that runs
  `make`.
- `AuthorizationPermissionMismatch`: regenerate the read-only SAS with both
  `r` and `l` permissions and confirm that it has not expired.
- `ContainerNotFound` or missing COCO JSON: run `azcopy list "$READ_URL"` and
  confirm that `images/` and `instances_train2017.json` are at the container
  root.
- Missing `adlfs`: run `uv sync --extra cloud-storage`.

### Clean Up Credentials

Remove credentials from the shell after testing:

```shell
unset UPLOAD_SAS UPLOAD_URL
unset READ_SAS READ_URL
unset FSSPEC_ABFS
```

Never commit SAS tokens or the populated `FSSPEC_ABFS` value.
