"""Read-efficiency and concurrency guarantees for image indexing.

These properties regress silently: an import that fetches whole objects to read a header, or
that reads them one at a time, still produces correct rows. Both are asserted here directly
against the fsspec layer rather than through wall-clock timing.
"""

from __future__ import annotations

import io
import threading
import time
from collections.abc import Callable
from typing import Any

import fsspec
import PIL.Image
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.file_outcome_report import (
    BrokenInputFileError,
    MissingInputFileError,
)
from lightly_studio.core.image import add_images
from lightly_studio.dataset import env
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import image_resolver

# Large enough that a whole-object read is unmistakable next to a header read.
_IMAGE_WIDTH = 1200
_IMAGE_HEIGHT = 800


def _jpeg_bytes(width: int = _IMAGE_WIDTH, height: int = _IMAGE_HEIGHT) -> bytes:
    """Return a JPEG whose body is far larger than its header."""
    buffer = io.BytesIO()
    # Noise resists JPEG compression, keeping the encoded body large.
    image = PIL.Image.frombytes(
        "RGB", (width, height), bytes((i * 7 + i // 3) % 256 for i in range(width * height * 3))
    )
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def _patch_url_to_fs(
    mocker: MockerFixture,
    on_open: Callable[[str, dict[str, Any]], io.BytesIO],
) -> None:
    """Route `fsspec.core.url_to_fs` to a fake filesystem whose open calls `on_open`.

    Args:
        mocker: The pytest-mock fixture.
        on_open: Receives the opened path and the keyword arguments `fs.open` was given, and
            returns the file contents to serve. Raise from it to simulate a failed open.
    """

    def fake_url_to_fs(path: str, **_kwargs: Any) -> tuple[Any, str]:
        filesystem = mocker.MagicMock()
        filesystem.open.side_effect = lambda _fs_path, _mode, **open_kwargs: on_open(
            path, open_kwargs
        )
        return filesystem, path

    mocker.patch.object(fsspec.core, "url_to_fs", side_effect=fake_url_to_fs)


def test_probe_image__reads_only_the_header_from_remote_storage(mocker: MockerFixture) -> None:
    """A dimension probe must not download the whole object.

    The s3fs default read-ahead block is 50 MiB and the read-ahead cache clamps its range to the
    object size, so an untuned header read fetches the entire image.
    """
    jpeg = _jpeg_bytes()
    requested_block_sizes: list[Any] = []

    def on_open(_path: str, open_kwargs: dict[str, Any]) -> io.BytesIO:
        requested_block_sizes.append(open_kwargs.get("block_size"))
        return io.BytesIO(jpeg)

    _patch_url_to_fs(mocker=mocker, on_open=on_open)

    result = add_images._probe_image("s3://bucket/image.jpg")

    assert result.error is None
    assert (result.width, result.height) == (_IMAGE_WIDTH, _IMAGE_HEIGHT)
    # The read-ahead block is capped, so the backend fetches a small range instead of the object.
    assert requested_block_sizes == [env.LIGHTLY_STUDIO_REMOTE_BLOCK_SIZE]
    assert len(jpeg) > env.LIGHTLY_STUDIO_REMOTE_BLOCK_SIZE


def test_probe_image__passes_no_block_size_for_local_paths(mocker: MockerFixture) -> None:
    """LocalFileSystem.open rejects block_size, so it must not be passed for local paths."""
    jpeg = _jpeg_bytes()
    open_kwargs_seen: list[dict[str, Any]] = []

    def on_open(_path: str, open_kwargs: dict[str, Any]) -> io.BytesIO:
        open_kwargs_seen.append(open_kwargs)
        return io.BytesIO(jpeg)

    _patch_url_to_fs(mocker=mocker, on_open=on_open)

    add_images._probe_image("/data/images/image.jpg")

    assert open_kwargs_seen == [{}]


def test_probe_image__reports_a_missing_file(mocker: MockerFixture) -> None:
    def on_open(path: str, _open_kwargs: dict[str, Any]) -> io.BytesIO:
        raise FileNotFoundError(path)

    _patch_url_to_fs(mocker=mocker, on_open=on_open)

    result = add_images._probe_image("s3://bucket/missing.jpg")

    assert isinstance(result.error, MissingInputFileError)


def test_probe_image__reports_a_broken_file(mocker: MockerFixture) -> None:
    _patch_url_to_fs(mocker=mocker, on_open=lambda _path, _open_kwargs: io.BytesIO(b"not an image"))

    result = add_images._probe_image("s3://bucket/broken.jpg")

    assert isinstance(result.error, BrokenInputFileError)


def test_load_into_dataset_from_paths__overlaps_slow_remote_reads(
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    """Reads must overlap, so total time tracks the slowest read, not their sum.

    Also asserts the peak number of simultaneously open reads directly, so the test fails for the
    right reason if the machine is merely slow.
    """
    jpeg = _jpeg_bytes(width=8, height=8)
    read_delay_seconds = 0.05
    image_count = 24

    concurrency_lock = threading.Lock()
    in_flight = 0
    peak_in_flight = 0

    def on_open(_path: str, _open_kwargs: dict[str, Any]) -> io.BytesIO:
        nonlocal in_flight, peak_in_flight
        with concurrency_lock:
            in_flight += 1
            peak_in_flight = max(peak_in_flight, in_flight)
        time.sleep(read_delay_seconds)
        with concurrency_lock:
            in_flight -= 1
        return io.BytesIO(jpeg)

    _patch_url_to_fs(mocker=mocker, on_open=on_open)

    paths = [f"s3://bucket/image_{index:03d}.jpg" for index in range(image_count)]
    started_at = time.perf_counter()
    sample_ids = add_images.load_into_dataset_from_paths(
        session=db_session,
        root_collection_id=collection.collection_id,
        image_paths=paths,
        show_progress=False,
    )
    elapsed_seconds = time.perf_counter() - started_at

    assert len(sample_ids) == image_count
    assert peak_in_flight > 1, "remote reads ran one at a time"
    # Serial reads would take image_count * read_delay_seconds; allow generous slack for the
    # database writes and scheduling so only a genuine loss of overlap fails this.
    assert elapsed_seconds < image_count * read_delay_seconds / 2


def test_load_into_dataset_from_paths__preserves_input_order(
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    """Returned sample IDs must follow input order; callers index into them positionally.

    Reads finish out of order here, so an unordered pool would reorder the result.
    """
    jpeg = _jpeg_bytes(width=8, height=8)
    image_count = 12

    def on_open(path: str, _open_kwargs: dict[str, Any]) -> io.BytesIO:
        # Earlier paths resolve last, so completion order is the reverse of input order.
        index = int(path.rsplit("_", maxsplit=1)[1].split(".", maxsplit=1)[0])
        time.sleep((image_count - index) * 0.005)
        return io.BytesIO(jpeg)

    _patch_url_to_fs(mocker=mocker, on_open=on_open)

    paths = [f"s3://bucket/image_{index:03d}.jpg" for index in range(image_count)]
    sample_ids = add_images.load_into_dataset_from_paths(
        session=db_session,
        root_collection_id=collection.collection_id,
        image_paths=paths,
        show_progress=False,
    )

    created = image_resolver.get_many_by_id(session=db_session, sample_ids=sample_ids)
    assert [sample.file_path_abs for sample in created] == paths
