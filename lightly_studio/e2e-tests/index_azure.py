"""Index the remote COCO example dataset from Azure Blob Storage."""

import os

import lightly_studio as ls
from lightly_studio import cloud_credentials

azure_credentials = os.environ.get("FSSPEC_ABFS")
if azure_credentials is None:
    raise RuntimeError("Set FSSPEC_ABFS to JSON containing the Azure account name and SAS token.")

cloud_credentials.apply_cloud_credentials(credentials={"FSSPEC_ABFS": azure_credentials})

ls.db_manager.connect(cleanup_existing=True)

dataset = ls.ImageDataset.create(name="azure_coco_dataset")
dataset.add_samples_from_coco(
    annotations_json="abfs://test/instances_train2017.json",
    images_path="abfs://test/images/",
    annotation_type=ls.AnnotationType.SEGMENTATION_MASK,
    embed=False,
    embed_annotations=False,
)

ls.start_gui()
