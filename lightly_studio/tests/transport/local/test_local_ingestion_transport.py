from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio.core.file_outcome_report import FileOutcome
from lightly_studio.database import db_manager
from lightly_studio.embed import embed_samples
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import image_resolver, tag_resolver, video_resolver
from lightly_studio.transport.ingestion_transport import IngestionTransport
from lightly_studio.transport.local.local_ingestion_transport import LocalIngestionTransport
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.video.helpers import create_video_file


@pytest.mark.usefixtures("patch_collection")
class TestLocalIngestionTransport:
    def test_add_images_from_path(self, tmp_path: Path) -> None:
        for name in ["cat/a.png", "cat/b.jpg", "dog/c.png"]:
            (tmp_path / name).parent.mkdir(exist_ok=True)
            Image.new("RGB", (4, 3)).save(tmp_path / name)
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        transport: IngestionTransport = LocalIngestionTransport()

        transport.add_images_from_path(
            collection_id=collection_id,
            path=str(tmp_path),
            allowed_extensions=[".PNG"],
            embed=False,
            tag_depth=1,
            limit=None,
        )

        images = image_resolver.get_all_by_collection_id(
            session=session, collection_id=collection_id
        ).samples
        assert sorted(image.file_name for image in images) == ["a.png", "c.png"]
        assert {(image.width, image.height) for image in images} == {(4, 3)}
        tag_names = tag_resolver.get_names_by_sample_ids(
            session=session, sample_ids=[image.sample_id for image in images]
        )
        assert sorted(names[0] for names in tag_names.values()) == ["cat", "dog"]

    def test_add_images_from_path__negative_tag_depth(self, tmp_path: Path) -> None:
        transport: IngestionTransport = LocalIngestionTransport()

        with pytest.raises(ValueError, match="tag_depth must be non-negative"):
            transport.add_images_from_path(
                collection_id=uuid4(),
                path=str(tmp_path),
                allowed_extensions=None,
                embed=False,
                tag_depth=-1,
                limit=None,
            )

    def test_add_images(self, tmp_path: Path) -> None:
        for name in ["new.png", "present.png"]:
            (tmp_path / name).touch()
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        create_image(
            session=session, collection_id=collection_id, file_path_abs=f"{tmp_path}/present.png"
        )
        images = [
            ImageCreate(file_name=name, file_path_abs=f"{tmp_path}/{name}", width=4, height=3)
            for name in ["new.png", "present.png", "new.png", "missing.png"]
        ]
        transport: IngestionTransport = LocalIngestionTransport()

        result = transport.add_images(collection_id=collection_id, images=images)

        assert result.outcomes == [
            FileOutcome.ADDED,
            FileOutcome.ALREADY_PRESENT,
            FileOutcome.ALREADY_PRESENT,
            FileOutcome.MISSING,
        ]
        new_image = image_resolver.get_by_id(
            session=session, sample_id=result.sample_ids[f"{tmp_path}/new.png"]
        )
        assert new_image is not None
        assert (new_image.width, new_image.height) == (4, 3)
        assert len(result.sample_ids) == 1

    def test_add_directory_tags(self, tmp_path: Path) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(
            session=session, collection_id=collection_id, file_path_abs=f"{tmp_path}/a/b/c.png"
        )
        transport: IngestionTransport = LocalIngestionTransport()

        transport.add_directory_tags(
            collection_id=collection_id,
            path=str(tmp_path),
            sample_ids=[image.sample_id],
            tag_depth=1,
        )

        tag_names = tag_resolver.get_names_by_sample_ids(
            session=session, sample_ids=[image.sample_id]
        )
        assert tag_names == {image.sample_id: ["a"]}

    def test_add_videos(self, tmp_path: Path) -> None:
        video_path = create_video_file(output_path=tmp_path / "a.mp4", num_frames=2)
        session = db_manager.persistent_session()
        collection_id = create_collection(
            session=session, sample_type=SampleType.VIDEO
        ).collection_id
        transport: IngestionTransport = LocalIngestionTransport()

        path_to_id = transport.add_videos(
            collection_id=collection_id,
            paths=[str(video_path), str(video_path)],
            embed_frames=False,
            target_fps=None,
        )

        video = video_resolver.get_by_id(session=session, sample_id=path_to_id[str(video_path)])
        assert video is not None
        assert len(video.frames) == 2
        assert len(path_to_id) == 1

    def test_embed_videos(self, mocker: MockerFixture) -> None:
        embed_video_samples = mocker.patch.object(embed_samples, "embed_video_samples")
        collection_id = uuid4()
        sample_ids = [uuid4()]
        transport: IngestionTransport = LocalIngestionTransport()

        transport.embed_videos(collection_id=collection_id, sample_ids=sample_ids)

        embed_video_samples.assert_called_once_with(
            session=db_manager.persistent_session(),
            collection_id=collection_id,
            sample_ids=sample_ids,
        )

    def test_embed_videos__empty_sample_ids(self, mocker: MockerFixture) -> None:
        embed_video_samples = mocker.patch.object(embed_samples, "embed_video_samples")
        transport: IngestionTransport = LocalIngestionTransport()

        transport.embed_videos(collection_id=uuid4(), sample_ids=[])

        embed_video_samples.assert_not_called()
