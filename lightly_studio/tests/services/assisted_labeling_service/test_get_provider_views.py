from __future__ import annotations

from lightly_studio.assisted_labeling import provider_ids
from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.services import assisted_labeling_service


def test_list_provider_views() -> None:
    views = assisted_labeling_service.list_provider_views()

    fake = FakeProvider()
    assert len(views) == 1
    assert views[0].provider_id == provider_ids.FAKE_PROVIDER_ID
    assert views[0].display_name == fake.display_name
    assert views[0].sends_data_to_third_party is False
    assert views[0].capabilities == fake.capabilities()
    assert views[0].unavailable_reason is None
