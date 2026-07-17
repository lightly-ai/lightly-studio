from __future__ import annotations

import logging
import posixpath
from pathlib import Path

import pytest
from labelformat.formats.labelformat import LabelformatObjectDetectionInput
from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.object_detection import ImageObjectDetection, SingleObjectDetection
from labelformat.utils import ImageDimensionError
from sqlmodel import Session

from lightly_studio.core.image import add_annotations
from lightly_studio.resolvers import annotation_resolver, image_resolver
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub


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


def test_normalize_images_root__local_path_is_posix() -> None:
    # On Windows, `str(Path(...).absolute())` returns backslashes which, when
    # joined with posix-separated labelformat filenames via `posixpath.join`,
    # produce mixed-separator strings that fail to match ingested paths.
    # The normalized root must therefore be in posix form.
    result = add_annotations.normalize_images_root(Path("some") / "images")

    assert "\\" not in result
    assert result.endswith("some/images")
    assert Path(result).is_absolute()


def test_normalize_images_root__joins_cleanly_with_posix_filename() -> None:
    root = add_annotations.normalize_images_root(Path("data") / "coco")
    joined = posixpath.join(root, "images/0001.jpg")

    assert "\\" not in joined
    assert joined.endswith("data/coco/images/0001.jpg")


def test_normalize_images_root__preserves_remote_protocol() -> None:
    result = add_annotations.normalize_images_root("s3://bucket/path")

    assert result == "s3://bucket/path"


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
