from __future__ import annotations

import pytest

from lightly_studio.database import db_manager
from lightly_studio.metadata.gps_coordinate import GPSCoordinate
from lightly_studio.resolvers import metadata_resolver
from lightly_studio.transport.local.local_metadata_transport import LocalMetadataTransport
from lightly_studio.transport.metadata_transport import MetadataTransport
from tests.helpers_resolvers import create_collection, create_image


@pytest.mark.usefixtures("patch_collection")
class TestLocalMetadataTransport:
    def test_get(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image_a = create_image(session=session, collection_id=collection_id, file_path_abs="/a")
        image_b = create_image(session=session, collection_id=collection_id, file_path_abs="/b")
        metadata_resolver.bulk_update_metadata(
            session=session,
            sample_metadata=[
                (image_a.sample_id, {"weather": "sunny", "gps": GPSCoordinate(lat=1.0, lon=2.0)})
            ],
        )
        transport: MetadataTransport = LocalMetadataTransport()

        metadata = transport.get(sample_ids=[image_a.sample_id, image_b.sample_id])

        assert list(metadata) == [image_a.sample_id]
        assert metadata[image_a.sample_id]["weather"] == "sunny"
        gps = metadata[image_a.sample_id]["gps"]
        assert isinstance(gps, GPSCoordinate)
        assert gps.as_dict() == {"lat": 1.0, "lon": 2.0}

    def test_update(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        transport: MetadataTransport = LocalMetadataTransport()
        transport.update(sample_metadata=[(image.sample_id, {"weather": "sunny", "count": 1})])

        transport.update(sample_metadata=[(image.sample_id, {"weather": "cloudy"})])

        assert transport.get(sample_ids=[image.sample_id]) == {
            image.sample_id: {"weather": "cloudy", "count": 1}
        }

    def test_update__type_mismatch(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        transport: MetadataTransport = LocalMetadataTransport()
        transport.update(sample_metadata=[(image.sample_id, {"count": 1})])

        with pytest.raises(ValueError, match=r"Expected integer, got string"):
            transport.update(sample_metadata=[(image.sample_id, {"count": "one"})])
