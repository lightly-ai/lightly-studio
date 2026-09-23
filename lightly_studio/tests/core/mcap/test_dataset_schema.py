from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.core.mcap import dataset_schema
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import mcap_group_component_definition_resolver
from tests.helpers_resolvers import create_collection

COMPONENTS = [
    McapComponentSpec(
        name="front",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/cam/front/compressed_video",
        camera_info_topic="/cam/front/camera_info",
    ),
    McapComponentSpec(
        name="pcl_front",
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic="/lidar/points",
        frame_id="livox_front_left",
    ),
]


def test_create_components(db_session: Session) -> None:
    group_collection = create_collection(session=db_session, sample_type=SampleType.GROUP)

    dataset_schema.create_components(
        session=db_session,
        group_collection_id=group_collection.collection_id,
        components=COMPONENTS,
    )

    assert mcap_group_component_definition_resolver.get_named_data_types_by_group_collection_id(
        session=db_session, group_collection_id=group_collection.collection_id
    ) == [(component.name, component.mcap_data_type) for component in COMPONENTS]


def test_create_components__duplicate_name(db_session: Session) -> None:
    group_collection = create_collection(session=db_session, sample_type=SampleType.GROUP)

    with pytest.raises(ValueError, match="Duplicate component name 'front'"):
        dataset_schema.create_components(
            session=db_session,
            group_collection_id=group_collection.collection_id,
            components=[
                McapComponentSpec(
                    name="front",
                    mcap_data_type=McapDataType.VIDEO_FRAME,
                    topic="/cam/front/compressed_video",
                ),
                McapComponentSpec(
                    name="front",
                    mcap_data_type=McapDataType.POINT_CLOUD,
                    topic="/lidar/points",
                ),
            ],
        )


def test_check_components_match(db_session: Session) -> None:
    group_collection = create_collection(session=db_session, sample_type=SampleType.GROUP)
    dataset_schema.create_components(
        session=db_session,
        group_collection_id=group_collection.collection_id,
        components=COMPONENTS,
    )

    dataset_schema.check_components_match(
        session=db_session,
        group_collection_id=group_collection.collection_id,
        components=COMPONENTS,
        dataset_name="perception",
    )


def test_check_components_match__other_data_type(db_session: Session) -> None:
    group_collection = create_collection(session=db_session, sample_type=SampleType.GROUP)
    dataset_schema.create_components(
        session=db_session,
        group_collection_id=group_collection.collection_id,
        components=COMPONENTS,
    )

    with pytest.raises(ValueError, match="were requested"):
        dataset_schema.check_components_match(
            session=db_session,
            group_collection_id=group_collection.collection_id,
            components=[
                McapComponentSpec(
                    name="front",
                    mcap_data_type=McapDataType.POINT_CLOUD,
                    topic="/cam/front/compressed_video",
                ),
                COMPONENTS[1],
            ],
            dataset_name="perception",
        )


def test_check_components_match__no_components(db_session: Session) -> None:
    group_collection = create_collection(session=db_session, sample_type=SampleType.GROUP)

    with pytest.raises(ValueError, match="already exists with the components no components"):
        dataset_schema.check_components_match(
            session=db_session,
            group_collection_id=group_collection.collection_id,
            components=COMPONENTS,
            dataset_name="perception",
        )
