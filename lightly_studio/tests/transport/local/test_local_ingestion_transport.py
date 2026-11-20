from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from lightly_studio.database import db_manager
from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.transport.ingestion_transport import IngestionTransport
from lightly_studio.transport.local.local_ingestion_transport import LocalIngestionTransport
from tests.helpers_resolvers import create_collection


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
