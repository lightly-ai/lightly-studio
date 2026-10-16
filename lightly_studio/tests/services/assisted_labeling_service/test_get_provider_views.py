from __future__ import annotations

from lightly_studio.assisted_labeling import provider_ids
from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.services import assisted_labeling_service


def test_list_provider_views() -> None:
    views = assisted_labeling_service.list_provider_views()

    fake = FakeProvider()
    by_id = {view.provider_id: view for view in views}
    assert provider_ids.FAL_SAM3_PROVIDER_ID in by_id
    view = by_id[provider_ids.FAKE_PROVIDER_ID]
    assert view.display_name == fake.display_name
    assert view.sends_data_to_third_party is False
    assert view.capabilities == fake.capabilities()
    assert view.unavailable_reason is None
