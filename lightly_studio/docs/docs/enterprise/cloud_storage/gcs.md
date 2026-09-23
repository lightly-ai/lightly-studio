# Google Cloud Storage Setup

This guide creates a Google Cloud service account with read-only access to a
Cloud Storage bucket. After downloading its JSON key, follow
[Cloud Storage](index.md#step-2-add-credentials-in-the-gui) to add it in the
LightlyStudio Enterprise GUI.

## Required Permissions

LightlyStudio needs these permissions on the bucket:

- `storage.objects.list` — list objects in the bucket
- `storage.objects.get` — read images and videos

The predefined
[Storage Object Viewer](https://cloud.google.com/storage/docs/access-control/iam-roles#storage.objectViewer)
role (`roles/storage.objectViewer`) contains both permissions. Grant it on only
the buckets LightlyStudio needs to read.

## Step 1: Create a Service Account

1. Open the
   [Service Accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts)
   in the Google Cloud console and select the project that owns the bucket.
2. Click **Create service account** and enter a name such as `LightlyStudio`.
3. Click **Create and continue**, then **Done**. You can grant bucket-level access
   in the next step instead of assigning a project-wide role.

See Google's
[service-account creation guide](https://cloud.google.com/iam/docs/service-accounts-create)
for the required administrative roles and other creation methods.

## Step 2: Grant Read Access to the Bucket

1. Open **Cloud Storage** → **Buckets** and select the bucket.
2. Open the **Permissions** tab and click **Grant access**.
3. Enter the service account email as the principal.
4. Select **Cloud Storage** → **Storage Object Viewer**, then save.

Repeat these steps for each bucket LightlyStudio must read.

## Step 3: Create a JSON Key

1. Return to the **Service Accounts** page and select the service account.
2. Open **Keys** → **Add key** → **Create new key**.
3. Select **JSON** and click **Create**. Google downloads the key once; store it
   securely until you add it to LightlyStudio.

!!! note
    Your organization might disable service-account key creation. If **Create new
    key** is unavailable, ask your Google Cloud administrator whether an exception
    is appropriate. See Google's
    [service-account key guide](https://cloud.google.com/iam/docs/keys-create-delete).

!!! warning
    A service-account JSON key is a long-lived secret. Do not commit it to source
    control or paste it into logs. Rotate it according to your organization's
    security policy and delete keys that are no longer used.

## Next Step

Open [Cloud Storage — Step 2](index.md#step-2-add-credentials-in-the-gui),
select **Google Cloud Storage**, and paste the complete downloaded JSON object.
After saving, Python clients can call `ls.connect()` and use paths such as
`gcs://my-bucket/images/`.
