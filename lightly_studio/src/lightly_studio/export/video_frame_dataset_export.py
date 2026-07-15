"""Exports video-frame datasets from Lightly Studio into various formats."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast
from uuid import UUID

from labelformat.model.image import Image
from sqlmodel import Session

from lightly_studio.core.sample import Sample
from lightly_studio.core.video.video_frame_sample import VideoFrameSample
from lightly_studio.export.dataset_export import DatasetExport


class VideoFrameDatasetExport(DatasetExport):
    """Provides methods to export a video-frame dataset or a subset of it.

    This class is typically not instantiated directly but returned by
    `VideoFrameDataset.export()`. It allows exporting data in various formats.
    """

    def __init__(
        self,
        session: Session,
        dataset_id: UUID,
        samples: Iterable[VideoFrameSample],
    ):
        """Initializes the VideoFrameDatasetExport object.

        Args:
            session: The database session.
            dataset_id: The dataset ID for label retrieval.
            samples: Samples to export.
        """
        super().__init__(
            session=session,
            dataset_id=dataset_id,
            samples=samples,
            sample_to_image=video_frame_to_image,
        )


def video_frame_to_image(sample: Sample, image_id: int, use_relative_filename: bool) -> Image:
    """Maps a video-frame sample to a labelformat `Image`.

    Conforms to the `SampleToImage` strategy, so `sample` is typed as `Sample`; it is always
    a `VideoFrameSample` here because this strategy is only used by `VideoFrameDatasetExport`.

    A frame has no file of its own, so the file name is synthesized from the parent video and
    the frame number (``<video>/<frame_number>.jpg``) and the dimensions are the parent video's.
    COCO stores the absolute video path verbatim; YOLO and Pascal VOC need a relative video name.
    """
    frame_sample = cast(VideoFrameSample, sample)
    video = frame_sample.parent_video
    video_reference = video.file_name if use_relative_filename else video.file_path_abs
    return Image(
        id=image_id,
        filename=f"{video_reference}/{frame_sample.frame_number:09d}.jpg",
        width=video.width,
        height=video.height,
    )
