"""Computes per-image quality metrics from pixels and stores them as metadata.

Every metric is a plain float computed from one decode of the image, so that the
distribution panel, the metadata filters, and ``metadata_weighting`` sampling can use
it without extra work. The metrics describe the pixels, they are not a good/bad
classifier: sharpness in particular depends on image scale and content, so compare it
between images of one dataset, do not apply one threshold to every dataset.

Definitions, all on the 8-bit RGB image after EXIF orientation is applied and any
alpha channel is discarded. ``L`` is Pillow's ``convert("L")`` luminance
(ITU-R BT.601: ``0.299 R + 0.587 G + 0.114 B``, rounded to an integer in ``[0, 255]``):

- ``brightness``: mean of ``L``, in ``[0, 255]``.
- ``contrast``: population standard deviation of ``L``, in ``[0, 127.5]``.
- ``sharpness``: variance of the 4-neighbour Laplacian ``4 L(x,y) - L(x-1,y) - L(x+1,y)
  - L(x,y-1) - L(x,y+1)`` over the interior pixels, in ``[0, inf)``. It is ``0.0`` for a
  constant image and for an image with fewer than 3 pixels in either dimension.
- ``entropy``: Shannon entropy of the 256-bin histogram of ``L``, in bits, in ``[0, 8]``.
- ``red_mean``, ``green_mean``, ``blue_mean``: per-channel means, in ``[0, 255]``.
- ``aspect_ratio``: ``width / height`` after EXIF orientation, in ``(0, inf)``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import fsspec
import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageOps
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import (
    BROKEN_IMAGE_ERRORS,
    FileOutcome,
    FileOutcomeReport,
)
from lightly_studio.dataset import remote_storage
from lightly_studio.resolvers import image_resolver, metadata_resolver
from lightly_studio.utils import batching, parallelize

logger = logging.getLogger(__name__)

# Bump when a metric definition changes. Samples computed with another version are
# recomputed on the next run, so results of two definitions never mix in one dataset.
IMAGE_QUALITY_METRICS_VERSION = 1
# Integer metadata key that records the version the sample's metrics were computed with.
IMAGE_QUALITY_VERSION_KEY = "image_quality_version"
# Decoding releases the GIL, so a few threads overlap on local files without oversubscribing.
DEFAULT_LOCAL_WORKERS = 4
# Metric dicts are small; one write per this many images keeps commits infrequent.
WRITE_BATCH_SIZE = 1_000
# The 4-neighbour Laplacian needs an interior pixel, so at least 3 pixels per side.
_MIN_LAPLACIAN_SIDE = 3


def compute_image_quality_metadata(
    session: Session,
    collection_id: UUID,
    overwrite: bool = False,
    max_workers: int | None = None,
) -> None:
    """Computes image quality metrics for each image in the collection.

    Each image is read once through fsspec and decoded once; all metrics come from that
    decode. Images are processed by a bounded thread pool and written in batches, so
    memory stays bounded for large collections. A missing or undecodable image gets no
    metric values, so it never looks like a dark or blurry image; the outcome is logged.

    Args:
        session:
            The database session.
        collection_id:
            The ID of the collection for which to compute the metrics.
        overwrite:
            If False, images that already carry metrics of the current
            ``IMAGE_QUALITY_METRICS_VERSION`` are skipped, so an interrupted run resumes.
            If True, every image is recomputed.
        max_workers:
            Number of images decoded concurrently. Defaults to
            ``DEFAULT_LOCAL_WORKERS`` for local files and to
            ``LIGHTLY_STUDIO_REMOTE_IMAGE_PROBE_WORKERS`` when any file is remote.

    Raises:
        AllInputFilesFailedError: If at least one image was attempted and none could
            be read.
        ValueError: If ``max_workers`` is less than 1.
    """
    inputs = _collect_inputs(session=session, collection_id=collection_id, overwrite=overwrite)
    paths = [image_input.path for image_input in inputs]
    remote_storage.configure_connections(paths=paths)
    if max_workers is None:
        max_workers = _default_workers(paths=paths)

    results = parallelize.thread_imap_lazy(
        function=_compute_one,
        iterable=inputs,
        max_workers=max_workers,
        buffer_size=max_workers,
    )
    report = FileOutcomeReport(label_overrides={FileOutcome.ADDED: "computed"})
    progress = tqdm(results, total=len(inputs), desc="Computing image quality", unit=" images")
    for batch in batching.batched(items=progress, batch_size=WRITE_BATCH_SIZE):
        _write_batch(session=session, results=batch, report=report)
    report.raise_if_all_failed()
    report.log_summary()


def compute_image_quality_metrics(image: Image.Image) -> dict[str, float]:
    """Computes the quality metrics of one decoded image.

    See the module docstring for the definition of every metric.

    Args:
        image: A decoded Pillow image in any mode.

    Returns:
        A mapping from metric name to its float value.
    """
    rgb = _normalize_image(image)
    width, height = rgb.size
    gray: NDArray[np.uint8] = np.asarray(rgb.convert("L"))
    channel_means = np.asarray(rgb, dtype=np.uint8).reshape(-1, 3).mean(axis=0)
    return {
        "brightness": float(gray.mean()),
        "contrast": float(gray.std()),
        "sharpness": _laplacian_variance(gray=gray),
        "entropy": _histogram_entropy(gray=gray),
        "red_mean": float(channel_means[0]),
        "green_mean": float(channel_means[1]),
        "blue_mean": float(channel_means[2]),
        "aspect_ratio": width / height,
    }


@dataclass(frozen=True)
class _ImageInput:
    """One image to process, with its filesystem resolved on the caller thread."""

    sample_id: UUID
    path: str
    filesystem: fsspec.AbstractFileSystem
    filesystem_path: str


@dataclass(frozen=True)
class _ImageResult:
    """The outcome of one image; ``metrics`` is set only for ``FileOutcome.ADDED``."""

    sample_id: UUID
    path: str
    outcome: FileOutcome
    metrics: dict[str, float] | None = None


def _collect_inputs(session: Session, collection_id: UUID, overwrite: bool) -> list[_ImageInput]:
    """List the images to process, skipping up-to-date ones unless ``overwrite``."""
    versions, _ = metadata_resolver.get_metadata_values_for_key(
        session=session, collection_id=collection_id, key=IMAGE_QUALITY_VERSION_KEY
    )
    samples = image_resolver.get_for_export(
        session=session, collection_id=collection_id, collection_filter=None
    )
    inputs = []
    for sample in samples:
        if not overwrite and versions.get(sample.sample_id) == IMAGE_QUALITY_METRICS_VERSION:
            continue
        # Resolve the filesystem here so worker threads share the cached client.
        filesystem, filesystem_path = fsspec.core.url_to_fs(sample.file_path_abs)
        inputs.append(
            _ImageInput(
                sample_id=sample.sample_id,
                path=sample.file_path_abs,
                filesystem=filesystem,
                filesystem_path=filesystem_path,
            )
        )
    return inputs


def _default_workers(paths: list[str]) -> int:
    """Return the configured remote worker count if any path is remote, else the local one."""
    if any(remote_storage.is_remote(path) for path in paths):
        return remote_storage.image_probe_workers(paths=paths)
    return DEFAULT_LOCAL_WORKERS


def _compute_one(image_input: _ImageInput) -> _ImageResult:
    """Read and decode one image and compute its metrics, classifying any file failure."""
    if not image_input.filesystem.exists(image_input.filesystem_path):
        return _ImageResult(
            sample_id=image_input.sample_id, path=image_input.path, outcome=FileOutcome.MISSING
        )
    try:
        with (
            image_input.filesystem.open(image_input.filesystem_path, mode="rb") as file,
            Image.open(file) as image,
        ):
            metrics = compute_image_quality_metrics(image=image)
    except BROKEN_IMAGE_ERRORS:
        return _ImageResult(
            sample_id=image_input.sample_id, path=image_input.path, outcome=FileOutcome.BROKEN
        )
    return _ImageResult(
        sample_id=image_input.sample_id,
        path=image_input.path,
        outcome=FileOutcome.ADDED,
        metrics=metrics,
    )


def _write_batch(
    session: Session, results: Iterable[_ImageResult], report: FileOutcomeReport
) -> None:
    """Record every outcome and write the metrics of the readable images in one call."""
    sample_metadata: list[tuple[UUID, Mapping[str, Any]]] = []
    for result in results:
        report.record(path=result.path, outcome=result.outcome)
        if result.metrics is None:
            continue
        metadata: dict[str, float | int] = dict(result.metrics)
        metadata[IMAGE_QUALITY_VERSION_KEY] = IMAGE_QUALITY_METRICS_VERSION
        sample_metadata.append((result.sample_id, metadata))
    metadata_resolver.bulk_update_metadata(session=session, sample_metadata=sample_metadata)


def _normalize_image(image: Image.Image) -> Image.Image:
    """Apply the EXIF orientation and convert to 8-bit RGB, discarding any alpha channel."""
    transposed = ImageOps.exif_transpose(image)
    assert transposed is not None
    return transposed.convert("RGB")


def _laplacian_variance(gray: NDArray[np.uint8]) -> float:
    """Variance of the 4-neighbour Laplacian over the interior pixels, 0.0 if there are none."""
    if gray.shape[0] < _MIN_LAPLACIAN_SIDE or gray.shape[1] < _MIN_LAPLACIAN_SIDE:
        return 0.0
    # Built in place so that only one float32 array the size of the interior is held.
    laplacian = np.multiply(gray[1:-1, 1:-1], 4.0, dtype=np.float32)
    np.subtract(laplacian, gray[:-2, 1:-1], out=laplacian)
    np.subtract(laplacian, gray[2:, 1:-1], out=laplacian)
    np.subtract(laplacian, gray[1:-1, :-2], out=laplacian)
    np.subtract(laplacian, gray[1:-1, 2:], out=laplacian)
    return float(laplacian.var(dtype=np.float64))


def _histogram_entropy(gray: NDArray[np.uint8]) -> float:
    """Shannon entropy in bits of the 256-bin histogram of ``gray``."""
    counts = np.bincount(gray.ravel(), minlength=256)
    probabilities = counts[counts > 0] / counts.sum()
    # max() turns the -0.0 of a single-bin histogram into 0.0.
    return max(0.0, float(-(probabilities * np.log2(probabilities)).sum()))
