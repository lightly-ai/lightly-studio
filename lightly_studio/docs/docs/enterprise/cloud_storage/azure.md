# Azure Blob Storage Setup

This guide creates a read-only shared access signature (SAS) for an Azure Blob
Storage container. After creating the token, follow
[Cloud Storage](index.md#step-2-add-credentials-in-the-gui) to add it in the
LightlyStudio Enterprise GUI.

## Required Permissions

LightlyStudio needs these permissions on the container:

- **Read** — read images and videos
- **List** — discover objects under dataset paths

Do not grant write, create, add, or delete permissions.

## Step 1: Create a Container SAS Token

1. Open the storage account in the
   [Azure portal](https://portal.azure.com/) and select **Data storage** →
   **Containers**.
2. Select the container LightlyStudio needs to read.
3. Open **Shared access tokens**.
4. Select only **Read** and **List** permissions.
5. Choose an expiration time that follows your organization's credential
   rotation policy, then generate the SAS token.
6. Store the generated **Blob SAS token** securely. It is a credential and must
   not be committed to source control or pasted into logs.

LightlyStudio currently stores one deployment-wide Azure credential set.
Configure the SAS token for the container that the deployment uses. Configuring
credentials for a second container replaces the existing credentials.

## Step 2: Record the Storage Account Name

Copy the storage account name from the Azure portal. Use only the name, such as
`mystorageaccount`, rather than the full `blob.core.windows.net` URL.

## Next Step

Open [Cloud Storage — Step 2](index.md#step-2-add-credentials-in-the-gui),
select **Azure Blob Storage**, and enter the storage account name and SAS token.
After saving, Python clients can call `ls.connect()` and use paths such as
`abfs://my-container/images/`.
