# Cloud Storage

This guide shows how to configure AWS S3 access for your LightlyStudio Enterprise instance so
that all Python clients can read images and videos directly from your S3 buckets.

The admin sets up the credentials once in the GUI. After that, every Python client that calls
`ls.connect()` receives them automatically — no per-user configuration needed.

## Step 1: Create an AWS IAM User

Create a dedicated IAM user with programmatic access for LightlyStudio.

1. Go to the
   [AWS IAM console](https://console.aws.amazon.com/iamv2/home?#/users)
   and create a new user. Choose a unique name and select **Programmatic access** as the
   access type.

    ![Create AWS User](https://files.readme.io/1fbecb0-UserAccess1.png){ width="100%" }

2. Click **Attach existing policies directly**, then **Create policy** to define a new
   policy for LightlyStudio.

    ![Setting user permissions](https://files.readme.io/8041107-UserAccess2.png){ width="100%" }

3. Switch to the **JSON** tab and paste the policy below. Replace `my-bucket` with
   the name of your S3 bucket.

    ```json title="lightly-s3-policy.json"
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": "s3:ListBucket",
          "Resource": "arn:aws:s3:::my-bucket"
        },
        {
          "Effect": "Allow",
          "Action": [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject"
          ],
          "Resource": "arn:aws:s3:::my-bucket/*"
        }
      ]
    }
    ```

    ![Permission policy JSON](https://files.readme.io/66b8155-UserAccess3.png){ width="100%" }

    !!! tip
        To restrict access to a specific folder, change the second resource to
        `arn:aws:s3:::my-bucket/my-folder/*`.

4. Click **Next**, add tags as you see fit, give your policy a name (e.g.
   `LightlyStudio-S3-Access`), and create it.

    ![Review and name policy](https://files.readme.io/2b79ebf-UserAccess4.png){ width="100%" }

5. Return to the user creation page, reload the policy list, and select the policy
   you just created. Continue creating the user.

    ![Attach policy to user](https://files.readme.io/10d1380-UserAccess5.png){ width="100%" }

6. Store the **Access Key ID** and **Secret Access Key** in a secure location. You will
   not be able to view the secret key again.

    ![Get security credentials](https://files.readme.io/2e57eab-UserAccess6.png){ width="100%" }

## Step 2: Add Credentials in the GUI

1. Open your LightlyStudio Enterprise instance in the browser.
2. Open the **Cloud Storage Credentials** dialog.
3. Enter the **Access Key ID** and **Secret Access Key** from the previous step.
4. Click **Save Credentials**.

![Cloud Storage Credentials dialog](../_static/cloud_storage_credentials_dialog.jpg){ width="100%" }

The credentials are now stored on the server and shared with all Python client connections.

## Step 3: Use Cloud Storage from Python

After calling `ls.connect()`, cloud credentials are injected into your local environment
automatically. You can use S3 paths directly — no extra setup needed on the client side.

```python title="enterprise_s3.py"
import lightly_studio as ls

ls.connect()

dataset = ls.ImageDataset.load_or_create("s3_dataset")
dataset.add_images_from_path(path="s3://my-bucket/images/")
```

!!! note
    The Python client must have the cloud storage dependencies installed:
    ```shell
    pip install "lightly-studio[cloud-storage]"
    ```
    See [Using Cloud Storage](../api/index.md#using-cloud-storage) for more details on
    supported cloud operations.
