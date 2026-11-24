from __future__ import annotations

import logging
from argparse import ArgumentParser
from collections.abc import Iterable
from pathlib import Path

import pytest
from labelformat.formats.labelformat import LabelformatObjectDetectionInput
from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.instance_segmentation import (
    ImageInstanceSegmentation,
    InstanceSegmentationInput,
    SingleInstanceSegmentation,
)
from labelformat.model.multipolygon import MultiPolygon
from labelformat.model.object_detection import ImageObjectDetection, SingleObjectDetection
from labelformat.utils import ImageDimensionError
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.image import add_annotations
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
    image_resolver,
)
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub


class _InstanceSegmentationInput(InstanceSegmentationInput):
    def __init__(
        self,
        categories: list[Category],
        images: list[Image],
        labels: list[ImageInstanceSegmentation],
    ) -> None:
        self._categories = categories
        self._images = images
        self._labels = labels

    @staticmethod
    def add_cli_arguments(parser: ArgumentParser) -> None:
        raise NotImplementedError

    def get_categories(self) -> Iterable[Category]:
        return self._categories

    def get_images(self) -> Iterable[Image]:
        return self._images

    def get_labels(self) -> Iterable[ImageInstanceSegmentation]:
        return self._labels


def test_skip_and_warn_unreadable_image__warns_on_image_dimension_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        add_annotations.skip_and_warn_unreadable_image(
            Path("broken.jpg"), ImageDimensionError("bad header", path="broken.jpg")
        )

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        "unreadable image" in r.getMessage() and "broken.jpg" in r.getMessage() for r in warnings
    )


def test_skip_and_warn_unreadable_image__reraises_other_error() -> None:
    # A non-dimension error is a bug or infra failure and must propagate, not be swallowed.
    with pytest.raises(ValueError, match="boom"):
        add_annotations.skip_and_warn_unreadable_image(Path("x.jpg"), ValueError("boom"))


def test_add_annotations_from_labelformat__resolved_path_and_collection_name(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(db_session)
    images = helpers_resolvers.create_images(
        db_session,
        collection.collection_id,
        [
            ImageStub(
                path=Path("images/image.jpg").absolute().as_posix(),
                width=100,
                height=200,
            ),
        ],
    )
    label_input = _get_labelformat_input_obj_det(filename="image.jpg")

    missing_paths = add_annotations.add_annotations_from_labelformat(
        session=db_session,
        root_collection_id=collection.collection_id,
        input_labels=label_input,
        images_root="images",
        collection_name="model_v1",
    )

    annotations = annotation_resolver.get_all_by_collection_name(
        session=db_session,
        collection_name="model_v1",
        parent_collection_id=collection.collection_id,
    ).annotations
    assert missing_paths == []
    assert len(annotations) == 1
    assert annotations[0].parent_sample_id == images[0].sample_id
    assert annotations[0].annotation_label.annotation_label_name == "dog"


def test_add_annotations_from_labelformat__missing_images(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(db_session)
    label_input = _get_labelformat_input_obj_det(filename="nonexistent.jpg")

    missing_paths = add_annotations.add_annotations_from_labelformat(
        session=db_session,
        root_collection_id=collection.collection_id,
        input_labels=label_input,
        images_root="/images",
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    ).samples
    images_root = Path("/images").absolute().as_posix()
    assert missing_paths == [f"{images_root}/nonexistent.jpg"]
    assert len(samples) == 0


def test_add_annotations_from_labelformat__marks_evaluation_run_stale(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(db_session)
    helpers_resolvers.create_images(
        db_session,
        collection.collection_id,
        [
            ImageStub(
                path=Path("images/image.jpg").absolute().as_posix(),
                width=100,
                height=200,
            ),
        ],
    )
    gt_collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="gt",
            sample_type=SampleType.ANNOTATION,
            parent_collection_id=collection.collection_id,
        ),
    )
    pred_collection = helpers_resolvers.create_collection(
        db_session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=collection.collection_id,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    assert run.stale_since is None

    add_annotations.add_annotations_from_labelformat(
        session=db_session,
        root_collection_id=collection.collection_id,
        input_labels=_get_labelformat_input_obj_det(filename="image.jpg"),
        images_root="images",
        collection_name="gt",
    )

    refreshed = evaluation_run_resolver.get_by_id(session=db_session, evaluation_id=run.id)
    assert refreshed is not None
    assert refreshed.stale_since is not None


def test_add_annotations_from_labelformat__one_warning_for_skipped(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mocker.patch.object(add_annotations, "SAMPLE_BATCH_SIZE", 2)
    collection = helpers_resolvers.create_collection(db_session)
    filenames = ["a.jpg", "b.jpg", "c.jpg"]
    helpers_resolvers.create_images(
        db_session,
        collection.collection_id,
        [
            ImageStub(path=Path(f"images/{name}").absolute().as_posix(), width=100, height=200)
            for name in filenames
        ],
    )
    label_input = _get_labelformat_input_instance_segmentation(filenames=filenames)

    with caplog.at_level(logging.WARNING):
        add_annotations.add_annotations_from_labelformat(
            session=db_session,
            root_collection_id=collection.collection_id,
            input_labels=label_input,
            images_root="images",
        )

    assert caplog.text.count("Skipped 3 polygon annotations") == 1


def _get_labelformat_input_obj_det(filename: str) -> LabelformatObjectDetectionInput:
    categories = [Category(id=0, name="dog")]
    image = Image(id=0, filename=filename, width=100, height=200)
    objects = [
        SingleObjectDetection(
            category=categories[0],
            box=BoundingBox(xmin=10.0, ymin=20.0, xmax=30.0, ymax=40.0),
        ),
    ]
    return LabelformatObjectDetectionInput(
        categories=categories,
        images=[image],
        labels=[ImageObjectDetection(image=image, objects=objects)],
    )


def _get_labelformat_input_instance_segmentation(
    filenames: list[str],
) -> _InstanceSegmentationInput:
    category = Category(id=0, name="dog")
    images = [
        Image(id=index, filename=filename, width=100, height=200)
        for index, filename in enumerate(filenames)
    ]
    # Each image has one polygon with 2 vertices, which is not valid.
    labels = [
        ImageInstanceSegmentation(
            image=image,
            objects=[
                SingleInstanceSegmentation(
                    category=category,
                    segmentation=MultiPolygon(polygons=[[(0.0, 0.0), (1.0, 1.0)]]),
                )
            ],
        )
        for image in images
    ]
    return _InstanceSegmentationInput(categories=[category], images=images, labels=labels)
