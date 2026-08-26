from __future__ import annotations

import io
import threading
import time

import fsspec
import PIL.Image
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.image import add_images
from lightly_studio.dataset import env
from lightly_studio.models.collection import CollectionTable


@pytest.mark.parametrize("protocol", ["s3", "gs", "az", "memory"])
def test_load_into_dataset_from_paths__bounds_remote_concurrency(
    protocol: str,
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    workers = 4
    peak_in_flight = _patch_filesystem(mocker=mocker)
    mocker.patch.object(env, "LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS", workers)
    mocker.patch.dict(fsspec.config.conf, {}, clear=True)

    sample_ids = add_images.load_into_dataset_from_paths(
        session=db_session,
        root_collection_id=collection.collection_id,
        image_paths=[f"{protocol}://bucket/image_{index}.png" for index in range(8)],
        show_progress=False,
    )

    assert len(sample_ids) == 8
    assert 1 < peak_in_flight[0] <= workers
    if protocol == "s3":
        assert fsspec.config.conf["s3"]["config_kwargs"]["max_pool_connections"] == workers
    else:
        assert "s3" not in fsspec.config.conf


def test_load_into_dataset_from_paths__keeps_local_reads_serial(
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    peak_in_flight = _patch_filesystem(mocker=mocker)
    mocker.patch.object(env, "LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS", 4)

    add_images.load_into_dataset_from_paths(
        session=db_session,
        root_collection_id=collection.collection_id,
        image_paths=[f"/images/image_{index}.png" for index in range(4)],
        show_progress=False,
    )

    assert peak_in_flight[0] == 1


def _patch_filesystem(mocker: MockerFixture) -> list[int]:
    image_bytes = io.BytesIO()
    PIL.Image.new("RGB", (8, 6)).save(image_bytes, format="PNG")
    lock = threading.Lock()
    in_flight = 0
    peak_in_flight = [0]

    def open_file(_path: str, _mode: str) -> io.BytesIO:
        nonlocal in_flight
        with lock:
            in_flight += 1
            peak_in_flight[0] = max(peak_in_flight[0], in_flight)
        time.sleep(0.01)
        with lock:
            in_flight -= 1
        return io.BytesIO(image_bytes.getvalue())

    filesystem = mocker.MagicMock()
    filesystem.exists.return_value = True
    filesystem.open.side_effect = open_file
    mocker.patch.object(
        fsspec.core,
        "url_to_fs",
        side_effect=lambda path: (filesystem, path),
    )
    return peak_in_flight
