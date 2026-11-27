"""End-to-end demonstration of the lightly_studio dataset loading and UI.

This module provides a simple example of how to load a COCO instance
segmentation dataset and launch the UI application for exploration and
visualization.
"""

import e2e_fixture

import lightly_studio as ls


def seed() -> None:
    """Create the general E2E fixture."""
    dataset = ls.ImageDataset.create()

    dataset.add_samples_from_coco(
        annotations_json="datasets/coco_subset_128_images/instances_train2017.json",
        images_path="datasets/coco_subset_128_images/images",
        annotation_task=ls.AnnotationFileTask.INSTANCE_SEGMENTATION,
    )


if __name__ == "__main__":
    e2e_fixture.run(seed=seed)
