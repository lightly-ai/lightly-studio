"""Usage tracking for sample ingestion.

Reports where ingested data comes from and in which format, never the path itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import fsspec

from lightly_studio.analytics import tracking
from lightly_studio.dataset import remote_storage
from lightly_studio.models.collection import SampleType
from lightly_studio.type_definitions import PathLike
from lightly_studio.utils import download

# Default folder of `download_example_dataset`. The quickstart and all docs examples use it.
# `quickstart_enterprise` reads the example data from `download.EXAMPLE_DATASET_HF_URI` instead.
EXAMPLE_DIR_NAME = "dataset_examples"


class IngestSourceKind(str, Enum):
    """Where ingested data comes from."""

    EXAMPLE = "example"
    LOCAL = "local"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class IngestFormat(str, Enum):
    """The format a dataset method reads."""

    FOLDER = "folder"
    COCO = "coco"
    COCO_CAPTION = "coco_caption"
    YOLO = "yolo"
    PASCAL_VOC = "pascal_voc"
    LABELFORMAT = "labelformat"
    LIGHTLY = "lightly"
    YOUTUBE_VIS = "youtube_vis"
    MCAP = "mcap"


@dataclass(frozen=True)
class IngestSource:
    """Where one ingest reads its data from.

    Attributes:
        kind: Example dataset, local folder or remote storage.
        protocol: Raw fsspec protocol, for example "s3" or "hf". Set only when `kind` is REMOTE.
    """

    kind: IngestSourceKind
    protocol: str | None = None


def get_source(path: PathLike) -> IngestSource:
    """Classify where the data of an ingest comes from.

    Call it on the path argument as the user gave it, before any normalization. `Path.absolute()`
    turns a remote URI such as "s3://bucket" into a local path.

    Never raises. Tracking is best effort and must not be able to break the ingest.

    Args:
        path: Path argument of the ingest method.

    Returns:
        The source of the data.
    """
    try:
        raw = str(path)
        example_uri = download.EXAMPLE_DATASET_HF_URI
        if raw == example_uri or raw.startswith(f"{example_uri}/"):
            return IngestSource(kind=IngestSourceKind.EXAMPLE)
        if remote_storage.is_remote(raw):
            return IngestSource(
                kind=IngestSourceKind.REMOTE, protocol=fsspec.utils.get_protocol(raw)
            )
        if EXAMPLE_DIR_NAME in Path(raw).parts:
            return IngestSource(kind=IngestSourceKind.EXAMPLE)
        return IngestSource(kind=IngestSourceKind.LOCAL)
    except Exception:
        return IngestSource(kind=IngestSourceKind.UNKNOWN)


def track_samples_ingested(
    source: IngestSource, sample_type: SampleType, ingest_format: IngestFormat
) -> None:
    """Report a finished ingest. Never raises.

    Args:
        source: Source of the data, from `get_source`.
        sample_type: Type of the ingested samples.
        ingest_format: Format the ingest method reads.
    """
    tracking.track(
        event=tracking.SAMPLES_INGESTED,
        properties=_to_properties(
            source=source, sample_type=sample_type, ingest_format=ingest_format
        ),
    )


def _to_properties(
    source: IngestSource, sample_type: SampleType, ingest_format: IngestFormat
) -> dict[str, str]:
    """Convert the event values to the strings PostHog receives."""
    properties = {
        "source": source.kind.value,
        "sample_type": sample_type.value,
        "format": ingest_format.value,
    }
    if source.protocol is not None:
        properties["protocol"] = source.protocol
    return properties
