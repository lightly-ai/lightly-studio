from __future__ import annotations

from pathlib import Path

from pytest_mock import MockerFixture

from lightly_studio.core.dataset_query.tags_expression import TagsContainsExpression
from lightly_studio.core.lightly_train_helpers import generate_train_script


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


def test_export_coco_for_tag__matches_tag_and_calls_export(mocker: MockerFixture) -> None:
    dataset = mocker.Mock()
    query = mocker.Mock()
    filtered_query = mocker.Mock()
    exporter = mocker.Mock()
    output_json_path = Path("/tmp/train_coco.json")

    dataset.query.return_value = query
    query.match.return_value = filtered_query
    dataset.export.return_value = exporter

    generate_train_script._export_coco_for_tag(
        dataset=dataset,
        tag_name="train",
        output_json_path=output_json_path,
    )

    assert query.match.call_count == 1
    # `match()` is called positionally with a TagsContainsExpression.
    match_expression = query.match.call_args.args[0]
    assert isinstance(match_expression, TagsContainsExpression)
    assert match_expression.tag_name == "train"

    dataset.export.assert_called_once_with(filtered_query)
    exporter.to_coco_object_detections.assert_called_once_with(output_json=output_json_path)
