from __future__ import annotations

from typing import Any

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.image import ImageTable
from lightly_studio.plugins.object_detection_autolabeling import ObjDetAutolabelingOperator
from lightly_studio.plugins.operator_registry import OperatorRegistry


class FakeModel:
    """Lightweight stand-in for the autolabeling model used in tests."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def predict(self, image_path: str, threshold: float = 0.6) -> dict[str, list[Any]]:
        self.calls.append(image_path)
        return {
            "labels": ["car"],
            "bboxes": [[0.0, 0.0, 1.0, 1.0]],
            "scores": [0.9],
        }


class DummyImage:
    """Context manager that mimics `PIL.Image.open` without reading files."""

    size = (640, 480)

    def __enter__(self) -> DummyImage:
        """Enter the context."""
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        """Exit the context."""
        return False


class FakePrepareCOCOEntries:
    """Captures calls to `predict_task_helpers.prepare_coco_entries`."""

    def __init__(self) -> None:
        self.prepared: list[tuple[dict[str, Any], tuple[int, int]]] = []

    def __call__(
        self, *, predictions: dict[str, Any], image_size: tuple[int, int]
    ) -> list[dict[str, Any]]:
        self.prepared.append((predictions, image_size))


class FakeSaveCOCOJSON:
    """Captures calls to `predict_task_helpers.save_coco_json`."""

    def __init__(self) -> None:
        self.saved: list[tuple[Any], str] = []

    def __call__(self, *, entries: list[dict[str, Any]], coco_filepath: str) -> None:
        self.saved.append((entries, coco_filepath))


def test_obj_det_autolabeling_operator(
    db_session: Session,
    dataset: DatasetTable,
    samples: list[ImageTable],
    monkeypatch,
) -> None:
    # Create a local registry and register a test operator
    operator_registry = OperatorRegistry()
    operator = ObjDetAutolabelingOperator()
    operator_registry.register(operator=operator)

    fake_model = FakeModel()
    fake_prepare_coco_entries = FakePrepareCOCOEntries()
    fake_save_coco_json = FakeSaveCOCOJSON()

    monkeypatch.setattr(
        "lightly_studio.plugins.object_detection_autolabeling.lightly_train.load_model",
        lambda _: fake_model,
    )
    monkeypatch.setattr(
        "lightly_studio.plugins.object_detection_autolabeling.Image.open",
        lambda _: DummyImage(),
    )
    monkeypatch.setattr(
        "lightly_studio.plugins.object_detection_autolabeling.predict_task_helpers.prepare_coco_entries",
        fake_prepare_coco_entries,
    )
    monkeypatch.setattr(
        "lightly_studio.plugins.object_detection_autolabeling.predict_task_helpers.save_coco_json",
        fake_save_coco_json,
    )

    result = operator.execute(
        session=db_session,
        dataset_id=dataset.dataset_id,
        parameters={"test flag": True, "test str": "test value"},
    )

    assert result.success
    assert result.message == "test value " + str(db_session) + " " + str(dataset.dataset_id)

    assert len(fake_model.calls) == len(samples)
    assert len(fake_save_coco_json.saved) == len(samples)
