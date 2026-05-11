from __future__ import annotations

import json
from pathlib import Path

import pytest

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.core.lightly_train_helpers import generate_train_script
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_images,
    create_tag,
)


def test_update_train_object_detection_template__renders_required_values() -> None:
    template_values = {
        "train_annotations": "/tmp/train_coco.json",
        "val_annotations": "/tmp/val_coco.json",
    }

    rendered = generate_train_script.update_train_object_detection_template(
        template_values=template_values
    )

    assert '"annotations": "/tmp/train_coco.json"' in rendered
    assert '"annotations": "/tmp/val_coco.json"' in rendered


def test_create_train_object_detection_script__writes_file(tmp_path: Path) -> None:
    output_script_path = tmp_path / "train_object_detection.py"
    template_values = {
        "train_annotations": "/tmp/train_coco.json",
        "val_annotations": "/tmp/val_coco.json",
    }

    generated_path = generate_train_script.create_train_object_detection_script(
        template_values=template_values,
        output_script_path=output_script_path,
    )

    assert generated_path == output_script_path
    assert output_script_path.exists()
    assert '"annotations": "/tmp/train_coco.json"' in output_script_path.read_text(encoding="utf-8")
    assert '"annotations": "/tmp/val_coco.json"' in output_script_path.read_text(encoding="utf-8")


@pytest.mark.usefixtures("patch_collection")
def test_export_coco_for_tag__exports_only_matching_tag(tmp_path: Path) -> None:
    dataset = ImageDataset.create(name="test_dataset")
    train_image, val_image = create_images(
        db_session=dataset.session,
        collection_id=dataset.collection_id,
        images=[
            ImageStub(path="train.jpg", width=100, height=100),
            ImageStub(path="val.jpg", width=200, height=200),
        ],
    )
    label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name="dog",
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=train_image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"x": 10, "y": 20, "width": 30, "height": 40},
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=val_image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"x": 50, "y": 60, "width": 70, "height": 80},
    )
    train_tag = create_tag(
        session=dataset.session,
        collection_id=dataset.collection_id,
        tag_name="train",
    )
    val_tag = create_tag(
        session=dataset.session,
        collection_id=dataset.collection_id,
        tag_name="val",
    )
    tag_resolver.add_tag_to_sample(
        session=dataset.session,
        tag_id=train_tag.tag_id,
        sample=train_image.sample,
    )
    tag_resolver.add_tag_to_sample(
        session=dataset.session,
        tag_id=val_tag.tag_id,
        sample=val_image.sample,
    )

    output_json_path = tmp_path / "train_coco.json"

    generate_train_script._export_coco_for_tag(
        dataset=dataset,
        tag_name="train",
        output_json_path=output_json_path,
    )

    assert json.loads(output_json_path.read_text()) == {
        "images": [
            {"id": 0, "file_name": "train.jpg", "width": 100, "height": 100},
        ],
        "categories": [{"id": 0, "name": "dog"}],
        "annotations": [
            {"image_id": 0, "category_id": 0, "bbox": [10.0, 20.0, 30.0, 40.0]},
        ],
    }
