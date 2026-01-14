from pathlib import Path

from PIL import Image as PILImage

from lightly_studio.core.add_samples import ImageCreateFromPath
from lightly_studio.core.add_videos import VideoCreateFromPath
from lightly_studio.core.group_dataset import GroupDataset
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.core.video_sample import VideoSample
from lightly_studio.models.collection import SampleType

# TODO: Do NOT import private functions
from .test_add_videos import _create_temp_video


class TestGroupDataset:
    def test_group_dataset(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        group_ds = GroupDataset.create(
            components=[
                ("img", SampleType.IMAGE),
                ("vid", SampleType.VIDEO),
                ("extra", SampleType.IMAGE),
            ],
            name="test_group_dataset",
        )

        # Create a test image and video files
        image_path = tmp_path / "image1.jpg"
        PILImage.new("RGB", (100, 100)).save(str(image_path))
        video_path = tmp_path / "video1.mp4"
        _create_temp_video(output_path=video_path, width=320, height=240, num_frames=10, fps=5)

        # Create a group sample
        group_ds.add_group_sample(
            components={
                "img": ImageCreateFromPath(path=str(image_path)),
                "vid": VideoCreateFromPath(path=str(video_path)),
            }
        )

        # Check that the group sample was added correctly
        samples = list(group_ds)
        assert len(samples) == 1
        group_sample = samples[0]
        img_sample = group_sample["img"]
        vid_sample = group_sample["vid"]
        extra_sample = group_sample["extra"]

        print(" Image Sample: ", img_sample)
        assert isinstance(img_sample, ImageSample)
        assert img_sample.file_name == "image1.jpg"

        print(" Video Sample: ", vid_sample)
        assert isinstance(vid_sample, VideoSample)
        assert vid_sample.file_name == "video1.mp4"
        assert vid_sample.fps == 5

        assert extra_sample is None
