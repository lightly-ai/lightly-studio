from __future__ import annotations

from sqlmodel import Session

from lightly_studio.assisted_labeling.provider import ProviderCapabilities
from lightly_studio.models.assisted_labeling import AssistedLabelingProviderView
from lightly_studio.services.assisted_labeling_service import get_provider_views
from tests.services.assisted_labeling_service import helpers


def test_get_active_provider_view(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")

    view = get_provider_views.get_active_provider_view(session=db_session)

    assert view == AssistedLabelingProviderView(
        provider_id="fake",
        display_name="Fake (offline)",
        sends_data_to_third_party=False,
        capabilities=ProviderCapabilities(
            positive_points=True,
            negative_points=True,
            boxes=True,
            text_prompt=True,
            max_instances=3,
        ),
        unavailable_reason=None,
    )


def test_list_provider_views() -> None:
    views = get_provider_views.list_provider_views()

    assert [view.provider_id for view in views] == [
        "fal_sam3",
        "fake",
    ]
    assert views[0].sends_data_to_third_party is True
