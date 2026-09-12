"""Test computing image quality metrics."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.metadata import compute_image_quality
from lightly_studio.resolvers import metadata_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images

# 8x8 checkerboard with 2x2 cells, drawn out so the expected values can be checked by hand.
_CHECKERBOARD = np.array(
    [
        [0, 0, 255, 255, 0, 0, 255, 255],
        [0, 0, 255, 255, 0, 0, 255, 255],
        [255, 255, 0, 0, 255, 255, 0, 0],
        [255, 255, 0, 0, 255, 255, 0, 0],
        [0, 0, 255, 255, 0, 0, 255, 255],
        [0, 0, 255, 255, 0, 0, 255, 255],
        [255, 255, 0, 0, 255, 255, 0, 0],
        [255, 255, 0, 0, 255, 255, 0, 0],
    ],
    dtype=np.uint8,
)


def test_compute_image_quality_metadata(db_session: Session, tmp_path: Path) -> None:
    collection = create_collection(session=db_session)
    gray_path = tmp_path / "gray.png"
    Image.new("RGB", (16, 8), color=(100, 100, 100)).save(gray_path)
    board_path = tmp_path / "board.png"
    Image.fromarray(_CHECKERBOARD).save(board_path)
    create_images(
        db_session,
        collection.collection_id,
        [ImageStub(path=str(gray_path)), ImageStub(path=str(board_path))],
    )

    compute_image_quality.compute_image_quality_metadata(
        session=db_session, collection_id=collection.collection_id
    )

    samples = {s.file_name: s for s in DatasetQuery(collection, db_session)}
    gray = samples["gray.png"]
    assert gray.metadata["brightness"] == 100.0
    assert gray.metadata["contrast"] == 0.0
    assert gray.metadata["sharpness"] == 0.0
    assert gray.metadata["entropy"] == 0.0
    assert gray.metadata["aspect_ratio"] == 2.0
    assert gray.metadata["image_quality_version"] == 1
    board = samples["board.png"]
    assert board.metadata["brightness"] == 127.5
    assert board.metadata["contrast"] == 127.5
    assert board.metadata["sharpness"] > 0.0
    assert board.metadata["entropy"] == 1.0
    # Every value is stored as a float so the schema type is stable across images.
    _, schema_type = metadata_resolver.get_metadata_values_for_key(
        session=db_session, collection_id=collection.collection_id, key="aspect_ratio"
    )
    assert schema_type == "float"


def test_compute_image_quality_metadata__missing_and_broken_get_no_values(
    db_session: Session, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    collection = create_collection(session=db_session)
    dark_path = tmp_path / "dark.png"
    Image.new("RGB", (8, 8), color=(0, 0, 0)).save(dark_path)
    broken_path = tmp_path / "broken.jpg"
    broken_path.write_bytes(b"not an image")
    missing_path = tmp_path / "missing.jpg"
    create_images(
        db_session,
        collection.collection_id,
        [ImageStub(path=str(p)) for p in (dark_path, broken_path, missing_path)],
    )

    with caplog.at_level(logging.INFO):
        compute_image_quality.compute_image_quality_metadata(
            session=db_session, collection_id=collection.collection_id
        )

    samples = {s.file_name: s for s in DatasetQuery(collection, db_session)}
    assert samples["dark.png"].metadata["brightness"] == 0.0
    # A failure must not become a zero that looks like a dark image.
    for file_name in ("broken.jpg", "missing.jpg"):
        assert samples[file_name].metadata["brightness"] is None
        assert samples[file_name].metadata["image_quality_version"] is None
    assert "computed=1, already_present=0, missing=1, broken=1" in caplog.text


def test_compute_image_quality_metadata__resumes_and_overwrites(
    db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    paths = [tmp_path / "a.png", tmp_path / "b.png"]
    for path in paths:
        Image.new("RGB", (8, 8), color=(50, 50, 50)).save(path)
    images = create_images(
        db_session, collection.collection_id, [ImageStub(path=str(p)) for p in paths]
    )
    compute_one = mocker.spy(compute_image_quality, "_compute_one")

    compute_image_quality.compute_image_quality_metadata(
        session=db_session, collection_id=collection.collection_id
    )
    assert compute_one.call_count == 2

    # A second run skips images that carry the current version.
    compute_image_quality.compute_image_quality_metadata(
        session=db_session, collection_id=collection.collection_id
    )
    assert compute_one.call_count == 2

    # An image computed with another version is recomputed.
    metadata_resolver.bulk_update_metadata(
        session=db_session,
        sample_metadata=[(images[0].sample_id, {"image_quality_version": 0})],
    )
    compute_image_quality.compute_image_quality_metadata(
        session=db_session, collection_id=collection.collection_id
    )
    assert compute_one.call_count == 3

    compute_image_quality.compute_image_quality_metadata(
        session=db_session, collection_id=collection.collection_id, overwrite=True
    )
    assert compute_one.call_count == 5


def test_compute_image_quality_metadata__writes_in_batches(
    db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    paths = [tmp_path / f"{i}.png" for i in range(3)]
    for path in paths:
        Image.new("RGB", (4, 4)).save(path)
    create_images(db_session, collection.collection_id, [ImageStub(path=str(p)) for p in paths])
    mocker.patch.object(compute_image_quality, "WRITE_BATCH_SIZE", 2)
    bulk_update = mocker.spy(metadata_resolver, "bulk_update_metadata")

    compute_image_quality.compute_image_quality_metadata(
        session=db_session, collection_id=collection.collection_id, max_workers=2
    )

    assert [len(call.kwargs["sample_metadata"]) for call in bulk_update.call_args_list] == [2, 1]


def test_compute_image_quality_metadata__all_failed_raises(
    db_session: Session, tmp_path: Path
) -> None:
    collection = create_collection(session=db_session)
    create_images(
        db_session, collection.collection_id, [ImageStub(path=str(tmp_path / "missing.jpg"))]
    )

    with pytest.raises(AllInputFilesFailedError):
        compute_image_quality.compute_image_quality_metadata(
            session=db_session, collection_id=collection.collection_id
        )


def test_compute_image_quality_metadata__unexpected_error_propagates(
    db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    path = tmp_path / "a.png"
    Image.new("RGB", (4, 4)).save(path)
    create_images(db_session, collection.collection_id, [ImageStub(path=str(path))])
    mocker.patch.object(
        compute_image_quality, "compute_image_quality_metrics", side_effect=RuntimeError("bug")
    )

    with pytest.raises(RuntimeError, match="bug"):
        compute_image_quality.compute_image_quality_metadata(
            session=db_session, collection_id=collection.collection_id
        )

    (sample,) = DatasetQuery(collection, db_session)
    assert sample.metadata["image_quality_version"] is None


def test_compute_image_quality_metadata__invalid_workers(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    with pytest.raises(ValueError, match="max_workers"):
        compute_image_quality.compute_image_quality_metadata(
            session=db_session, collection_id=collection.collection_id, max_workers=0
        )


def test_compute_image_quality_metrics__constant_gray() -> None:
    metrics = compute_image_quality.compute_image_quality_metrics(
        image=Image.new("RGB", (6, 3), color=(128, 128, 128))
    )

    assert metrics == {
        "brightness": 128.0,
        "contrast": 0.0,
        "sharpness": 0.0,
        "entropy": 0.0,
        "red_mean": 128.0,
        "green_mean": 128.0,
        "blue_mean": 128.0,
        "aspect_ratio": 2.0,
    }


def test_compute_image_quality_metrics__checkerboard() -> None:
    metrics = compute_image_quality.compute_image_quality_metrics(
        image=Image.fromarray(_CHECKERBOARD)
    )

    assert metrics["brightness"] == 127.5
    assert metrics["contrast"] == 127.5
    # Two equally likely gray levels carry exactly one bit.
    assert metrics["entropy"] == 1.0
    # With 2x2 cells every interior pixel has one same and one opposite neighbour per axis,
    # so its Laplacian is +-2 * 255. The mean is 0, so the variance is the square of that.
    assert metrics["sharpness"] == pytest.approx((2 * 255) ** 2)


def test_compute_image_quality_metrics__blurred_is_less_sharp() -> None:
    board = Image.fromarray(_CHECKERBOARD)
    blurred = board.resize((4, 4), Image.Resampling.BILINEAR).resize(
        (8, 8), Image.Resampling.BILINEAR
    )

    sharp = compute_image_quality.compute_image_quality_metrics(image=board)
    soft = compute_image_quality.compute_image_quality_metrics(image=blurred)

    assert 0.0 < soft["sharpness"] < sharp["sharpness"]
    assert soft["contrast"] < sharp["contrast"]


def test_compute_image_quality_metrics__colour_channels() -> None:
    metrics = compute_image_quality.compute_image_quality_metrics(
        image=Image.new("RGB", (2, 2), color=(255, 0, 0))
    )

    assert metrics["red_mean"] == 255.0
    assert metrics["green_mean"] == 0.0
    assert metrics["blue_mean"] == 0.0
    # Pillow's BT.601 luminance of pure red, rounded to 8 bit.
    assert metrics["brightness"] == 76.0


def test_compute_image_quality_metrics__exif_orientation_applied(tmp_path: Path) -> None:
    path = tmp_path / "rotated.png"
    exif = Image.Exif()
    exif[0x0112] = 6  # Rotate 90 degrees clockwise on display.
    Image.new("RGB", (4, 2)).save(path, exif=exif)

    with Image.open(path) as image:
        metrics = compute_image_quality.compute_image_quality_metrics(image=image)

    assert metrics["aspect_ratio"] == 0.5


def test_compute_image_quality_metrics__alpha_discarded() -> None:
    metrics = compute_image_quality.compute_image_quality_metrics(
        image=Image.new("RGBA", (2, 2), color=(255, 255, 255, 0))
    )

    assert metrics["brightness"] == 255.0


def test_compute_image_quality_metrics__too_small_for_laplacian() -> None:
    metrics = compute_image_quality.compute_image_quality_metrics(
        image=Image.fromarray(_CHECKERBOARD[:2, :])
    )

    assert metrics["sharpness"] == 0.0
    assert metrics["contrast"] == 127.5
