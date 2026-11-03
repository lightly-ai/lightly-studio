from __future__ import annotations

import pytest

from lightly_studio.transport.local.local_collection_transport import LocalCollectionTransport
from lightly_studio.transport.local.local_transport import LocalTransport


class TestLocalTransport:
    def test_collections(self) -> None:
        assert isinstance(LocalTransport().collections, LocalCollectionTransport)

    @pytest.mark.parametrize("area", ["samples", "tags", "metadata"])
    def test_area__not_implemented(self, area: str) -> None:
        with pytest.raises(NotImplementedError):
            getattr(LocalTransport(), area)
