from __future__ import annotations

import pytest

from lightly_studio.database import db_manager
from lightly_studio.transport.compute_transport import ComputeTransport
from lightly_studio.transport.local.local_compute_transport import LocalComputeTransport
from tests.helpers_resolvers import create_collection


@pytest.mark.usefixtures("patch_collection")
class TestLocalComputeTransport:
    def test_compute_similarity__unknown_tag(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        transport: ComputeTransport = LocalComputeTransport()

        with pytest.raises(ValueError, match=r"Query tag not found"):
            transport.compute_similarity(
                collection_id=collection_id,
                query_tag_name="query",
                embedding_model_name=None,
                metadata_name=None,
            )
