from pathlib import Path

import pytest
from PIL import Image as PILImage

from lightly_studio import db_manager
from lightly_studio.core.group.group_dataset import GroupDataset
from lightly_studio.core.group.group_sample import GroupSample
from lightly_studio.core.image.create_image import CreateImage
from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.core.video.create_video import CreateVideo
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import create_video_file


class TestGroupDataset:
    def test_create(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        group_ds = GroupDataset.create(
            components=[
                ("img", SampleType.IMAGE),
                ("vid", SampleType.VIDEO),
            ],
            name="test_group_dataset",
        )
        dataset_id = group_ds.dataset_id

        assert group_ds.sample_type() == SampleType.GROUP
        assert group_ds.sample_class() == GroupSample

        session = group_ds.session
        component_cols = collection_resolver.get_group_components(
            session=session, parent_collection_id=dataset_id
        )
        assert len(component_cols) == 2
        assert component_cols["img"].sample_type == SampleType.IMAGE
        assert component_cols["vid"].sample_type == SampleType.VIDEO

    def test_load(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        session = db_manager.persistent_session()
        group_col = create_collection(
            session=session, sample_type=SampleType.GROUP, collection_name="test_group_dataset"
        )

        group_ds = GroupDataset.load(name="test_group_dataset")

        assert group_ds.dataset_id == group_col.collection_id
        assert group_ds.name == "test_group_dataset"

    def test_load_or_create(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        # First call creates the dataset
        group_ds_1 = GroupDataset.load_or_create(components=[("img", SampleType.IMAGE)])

        # Second call loads the existing dataset
        group_ds_2 = GroupDataset.load_or_create(components=[("img", SampleType.IMAGE)])
        assert group_ds_1.dataset_id == group_ds_2.dataset_id

        # Mismatched schema raises ValueError
        with pytest.raises(
            ValueError, match=r"already exists with a different number of components \(1 vs 2\)."
        ):
            GroupDataset.load_or_create(
                components=[("img", SampleType.IMAGE), ("extra", SampleType.IMAGE)]
            )
        with pytest.raises(
            ValueError, match=r"Key 'vid' with type 'image' not found in existing dataset."
        ):
            GroupDataset.load_or_create(components=[("vid", SampleType.IMAGE)])
        with pytest.raises(
            ValueError, match=r"Key 'img' with type 'video' not found in existing dataset."
        ):
            GroupDataset.load_or_create(components=[("img", SampleType.VIDEO)])

    def test_add_group_sample(
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
        PILImage.new(mode="RGB", size=(10, 10)).save(str(image_path))
        video_path = tmp_path / "video1.mp4"
        create_video_file(output_path=video_path, fps=5)

        # Create an incomplete and an empty group sample
        group_sample = group_ds.add_group_sample(
            components={
                "img": CreateImage(path=str(image_path)),
                "vid": CreateVideo(path=str(video_path)),
            }
        )

        # Check that the group sample was added correctly
        img_sample = group_sample["img"]
        vid_sample = group_sample["vid"]
        extra_sample = group_sample["extra"]

        assert isinstance(img_sample, ImageSample)
        assert img_sample.file_name == "image1.jpg"

        assert isinstance(vid_sample, VideoSample)
        assert vid_sample.file_name == "video1.mp4"
        assert vid_sample.fps == 5

        assert extra_sample is None

        # Add an empty group sample
        empty_sample = group_ds.add_group_sample(components={})
        assert empty_sample["img"] is None
        assert empty_sample["vid"] is None
        assert empty_sample["extra"] is None

    def test_iter_and_slice(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        group_ds = GroupDataset.create(
            components=[("img", SampleType.IMAGE)],
            name="test_group_dataset",
        )

        # Create test image files
        PILImage.new(mode="RGB", size=(10, 10)).save(str(tmp_path / "image1.jpg"))
        PILImage.new(mode="RGB", size=(10, 10)).save(str(tmp_path / "image2.jpg"))
        PILImage.new(mode="RGB", size=(10, 10)).save(str(tmp_path / "image3.jpg"))

        # Add samples
        group_ds.add_group_sample(
            components={"img": CreateImage(path=str(tmp_path / "image1.jpg"))}
        )
        group_ds.add_group_sample(
            components={"img": CreateImage(path=str(tmp_path / "image2.jpg"))}
        )
        group_ds.add_group_sample(
            components={"img": CreateImage(path=str(tmp_path / "image3.jpg"))}
        )

        # Get all samples via iteration
        samples = list(group_ds)
        assert isinstance(samples[0]["img"], ImageSample)
        assert isinstance(samples[1]["img"], ImageSample)
        assert isinstance(samples[2]["img"], ImageSample)
        assert {
            samples[0]["img"].file_name,
            samples[1]["img"].file_name,
            samples[2]["img"].file_name,
        } == {"image1.jpg", "image2.jpg", "image3.jpg"}

        # Get a slice of samples. We can't order groups yet, so we just check the length.
        sliced_samples = list(group_ds[1:3])
        assert len(sliced_samples) == 2
