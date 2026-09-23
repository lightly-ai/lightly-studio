from __future__ import annotations

import pytest

from lightly_studio.core.mcap.create_mcap import CreateMcap
from lightly_studio.core.mcap.group_dataset import McapGroupDataset
from lightly_studio.core.mcap.mcap_sample import McapSample
from lightly_studio.database import db_manager
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_component_definition_resolver,
)

COMPONENTS = [
    ("front", McapDataType.VIDEO_FRAME),
    ("pcl_front", McapDataType.POINT_CLOUD),
]


class TestMcapGroupDataset:
    def test_get_component(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        group_dataset = _create_mcap_group_dataset()

        front = group_dataset.get_component(name="front")
        pcl_front = group_dataset.get_component(name="pcl_front")

        assert front.name == "front"
        assert front.mcap_data_type == McapDataType.VIDEO_FRAME
        assert pcl_front.name == "pcl_front"
        assert pcl_front.mcap_data_type == McapDataType.POINT_CLOUD
        assert front.collection_id != pcl_front.collection_id

    def test_get_component__unknown_name(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        group_dataset = _create_mcap_group_dataset()

        with pytest.raises(KeyError, match="Known components: front, pcl_front"):
            group_dataset.get_component(name="rear")

    def test_add_group_sample(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        group_dataset = _create_mcap_group_dataset()

        group_sample = group_dataset.add_group_sample(
            components={
                "front": CreateMcap(
                    channel_id=1,
                    log_time_ns=1_000_000_000,
                    capture_timestamp_ns=1_000_000_000,
                    keyframe_log_time_ns=1_000_000_000,
                ),
                "pcl_front": CreateMcap(
                    channel_id=2,
                    log_time_ns=1_050_000_000,
                    capture_timestamp_ns=1_050_000_000,
                ),
            }
        )

        front_sample = group_sample["front"]
        assert isinstance(front_sample, McapSample)
        assert front_sample.channel_id == 1


def _create_mcap_group_dataset() -> McapGroupDataset:
    """Create a group dataset with MCAP component definitions."""
    group_dataset = McapGroupDataset.create(
        components=[(name, SampleType.MCAP) for name, _ in COMPONENTS],
        name="perception_groups",
    )
    session = db_manager.persistent_session()
    component_collections = collection_resolver.get_group_components(
        session=session, parent_collection_id=group_dataset.collection_id
    )
    for name, mcap_data_type in COMPONENTS:
        mcap_group_component_definition_resolver.create(
            session=session,
            collection_id=component_collections[name].collection_id,
            mcap_data_type=mcap_data_type,
        )
    return group_dataset
