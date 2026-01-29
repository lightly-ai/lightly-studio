from pathlib import Path

from PIL import Image as PILImage
from sqlmodel import Session

from lightly_studio.core.create_image import CreateImage
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import create_collection


class TestCreateImage:
    def test_create_in_collection(self, db_session: Session, tmp_path: Path) -> None:
        # Create a test image file.
        img = PILImage.new(mode="RGB", size=(100, 100), color="red")
        img.save(tmp_path / "test_image.jpg")

        # Create an image sample.
        ds = create_collection(session=db_session)
        creator = CreateImage(path=str(tmp_path / "test_image.jpg"))
        sample_id = creator.create_in_collection(session=db_session, collection_id=ds.collection_id)

        # Verify the image sample was created correctly.
        result = image_resolver.get_all_by_collection_id(
            session=db_session, collection_id=ds.collection_id
        )
        assert result.total_count == 1

        sample = result.samples[0]
        assert sample.sample_id == sample_id
        assert sample.file_name == "test_image.jpg"
        assert sample.width == 100
        assert sample.height == 100

    def test_sample_type(self) -> None:
        creator = CreateImage(path="dummy_path.jpg")
        assert creator.sample_type() == SampleType.IMAGE
