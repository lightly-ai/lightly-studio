"""Tests for cuboids_in_frame."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import Session

from lightly_studio.core.mcap.errors import McapAccessError, TransformNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.models.annotation.annotation_base import AnnotationType, AnnotationView
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationView
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationView
from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.static_transform import StaticTransformCreate
from lightly_studio.resolvers import recording_resolver, static_transform_resolver
from lightly_studio.services.recording_service import cuboids_in_frame
from tests.core.mcap import helpers as mcap_helpers
from tests.helpers_resolvers import create_collection

CUBOID_IN_ODOM = Cuboid3DAnnotationView(
    frame_id="odom",
    px=0.0,
    py=0.0,
    pz=0.5,
    qx=0.0,
    qy=0.0,
    qz=0.0,
    qw=1.0,
    sx=2.0,
    sy=1.0,
    sz=1.5,
)
CUBOID_IN_LIDAR = CUBOID_IN_ODOM.model_copy(update={"frame_id": mcap_helpers.LIDAR_FRAME_ID})
BOUNDING_BOX = ObjectDetectionAnnotationView(x=10.0, y=20.0, width=30.0, height=40.0)


def test_cuboids_in_frame(db_session: Session, tmp_path: Path) -> None:
    mcap_path = mcap_helpers.write_mcap(
        path=tmp_path / "with_tf.mcap",
        base_link_poses=[
            (1_000_000_000, (10.0, 0.0, 0.0)),
            (1_050_000_000, (20.0, 0.0, 0.0)),
        ],
    )
    recording_id = _create_recording(session=db_session, uri=str(mcap_path))
    static_transform_resolver.create_many(
        session=db_session,
        rows=[
            # The lidar sits at (0, 1, 2) m in the base frame, turned by 90 degrees.
            StaticTransformCreate(
                recording_id=recording_id,
                parent=mcap_helpers.BASE_FRAME_ID,
                child=mcap_helpers.LIDAR_FRAME_ID,
                qx=0.0,
                qy=0.0,
                qz=0.7071067811865476,
                qw=0.7071067811865476,
                tx=0.0,
                ty=1.0,
                tz=2.0,
            ),
            # The odom frame is the map frame.
            StaticTransformCreate(
                recording_id=recording_id,
                parent=mcap_helpers.WORLD_FRAME_ID,
                child="odom",
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=0.0,
                ty=0.0,
                tz=0.0,
            ),
        ],
    )
    cuboid_in_odom = _annotation_view(cuboid=CUBOID_IN_ODOM)
    cuboid_in_lidar = _annotation_view(cuboid=CUBOID_IN_LIDAR)
    bounding_box = _annotation_view(bounding_box=BOUNDING_BOX)

    result = cuboids_in_frame.cuboids_in_frame(
        session=db_session,
        recording_id=recording_id,
        annotations=[cuboid_in_odom, cuboid_in_lidar, bounding_box],
        target_frame_id=mcap_helpers.LIDAR_FRAME_ID,
        timestamp_ns=1_050_000_000,
    )

    assert len(result) == 3
    cuboid = result[0].cuboid_3d_details
    assert cuboid is not None
    assert result[0].sample_id == cuboid_in_odom.sample_id
    assert cuboid.frame_id == mcap_helpers.LIDAR_FRAME_ID
    # The cuboid at (0, 0, 0.5) m in the map is at (-20, -1, -1.5) m from the lidar at
    # 1.05 s. The lidar is turned by 90 degrees, so x and y swap and the cuboid turns back.
    assert (cuboid.px, cuboid.py, cuboid.pz) == pytest.approx((-1.0, 20.0, -1.5))
    assert (cuboid.qx, cuboid.qy, cuboid.qz, cuboid.qw) == pytest.approx(
        (0.0, 0.0, -0.7071067811865476, 0.7071067811865476)
    )
    assert (cuboid.sx, cuboid.sy, cuboid.sz) == pytest.approx((2.0, 1.0, 1.5))
    assert result[1] == cuboid_in_lidar
    assert result[2] == bounding_box


def test_cuboids_in_frame__nothing_to_map(db_session: Session) -> None:
    # The recording does not exist and the tick has no timestamp, so the test fails if
    # the function tries to map a cuboid.
    annotations = [
        _annotation_view(cuboid=CUBOID_IN_ODOM),
        _annotation_view(bounding_box=BOUNDING_BOX),
    ]

    result = cuboids_in_frame.cuboids_in_frame(
        session=db_session,
        recording_id=uuid.uuid4(),
        annotations=annotations,
        target_frame_id="odom",
        timestamp_ns=None,
    )

    assert result == annotations


def test_cuboids_in_frame__without_timestamp(db_session: Session) -> None:
    with pytest.raises(McapAccessError, match="The tick has no timestamp"):
        cuboids_in_frame.cuboids_in_frame(
            session=db_session,
            recording_id=uuid.uuid4(),
            annotations=[_annotation_view(cuboid=CUBOID_IN_ODOM)],
            target_frame_id=mcap_helpers.LIDAR_FRAME_ID,
            timestamp_ns=None,
        )


def test_cuboids_in_frame__unknown_recording(db_session: Session) -> None:
    recording_id = uuid.uuid4()

    with pytest.raises(McapAccessError, match=f"Recording {recording_id} was not found"):
        cuboids_in_frame.cuboids_in_frame(
            session=db_session,
            recording_id=recording_id,
            annotations=[_annotation_view(cuboid=CUBOID_IN_ODOM)],
            target_frame_id=mcap_helpers.LIDAR_FRAME_ID,
            timestamp_ns=1_000,
        )


def test_cuboids_in_frame__not_connected(db_session: Session, tmp_path: Path) -> None:
    # No static transforms are stored and the recording has no `/tf` topic.
    mcap_path = mcap_helpers.write_mcap(path=tmp_path / "recording.mcap")
    recording_id = _create_recording(session=db_session, uri=str(mcap_path))

    with pytest.raises(TransformNotFoundError):
        cuboids_in_frame.cuboids_in_frame(
            session=db_session,
            recording_id=recording_id,
            annotations=[_annotation_view(cuboid=CUBOID_IN_ODOM)],
            target_frame_id=mcap_helpers.LIDAR_FRAME_ID,
            timestamp_ns=1_050_000_000,
        )


def test_map_cuboids(tmp_path: Path) -> None:
    # The recording has no `/tf` topic, so the cuboid can only be mapped with the
    # given dynamic edge.
    mcap_path = mcap_helpers.write_mcap(path=tmp_path / "recording.mcap")
    # The odom frame is 1 m ahead of the map frame.
    odom_in_map = StaticTransform(
        parent_frame_id=mcap_helpers.WORLD_FRAME_ID,
        child_frame_id="odom",
        translation=(1.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0, 1.0),
        timestamp_ns=0,
    )
    # The base frame is 10 m ahead of the map frame at 1.05 s.
    base_in_map = StaticTransform(
        parent_frame_id=mcap_helpers.WORLD_FRAME_ID,
        child_frame_id=mcap_helpers.BASE_FRAME_ID,
        translation=(10.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0, 1.0),
        timestamp_ns=1_050_000_000,
    )
    cuboid_in_odom = _annotation_view(cuboid=CUBOID_IN_ODOM)
    bounding_box = _annotation_view(bounding_box=BOUNDING_BOX)

    with McapFileReader(mcap_path) as reader:
        result = cuboids_in_frame.map_cuboids(
            reader=reader,
            annotations=[cuboid_in_odom, bounding_box],
            target_frame_id=mcap_helpers.BASE_FRAME_ID,
            timestamp_ns=1_050_000_000,
            static_transforms=[odom_in_map],
            dynamic_transforms=[base_in_map],
        )

    assert len(result) == 2
    cuboid = result[0].cuboid_3d_details
    assert cuboid is not None
    assert cuboid.frame_id == mcap_helpers.BASE_FRAME_ID
    # The cuboid at (0, 0, 0.5) m in odom is at (1, 0, 0.5) m in the map, and at
    # (-9, 0, 0.5) m from the base.
    assert (cuboid.px, cuboid.py, cuboid.pz) == pytest.approx((-9.0, 0.0, 0.5))
    assert result[1] == bounding_box


def test_map_cuboids__not_connected(tmp_path: Path) -> None:
    mcap_path = mcap_helpers.write_mcap(path=tmp_path / "recording.mcap")

    with McapFileReader(mcap_path) as reader, pytest.raises(TransformNotFoundError):
        cuboids_in_frame.map_cuboids(
            reader=reader,
            annotations=[_annotation_view(cuboid=CUBOID_IN_ODOM)],
            target_frame_id=mcap_helpers.LIDAR_FRAME_ID,
            timestamp_ns=1_050_000_000,
            static_transforms=[],
            dynamic_transforms=[],
        )


def _create_recording(session: Session, uri: str) -> uuid.UUID:
    """Creates a recording of `uri` in a new dataset."""
    collection = create_collection(session=session, sample_type=SampleType.SEQUENCE)
    return recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri=uri,
        format_=RecordingFormat.MCAP,
    )


def _annotation_view(
    cuboid: Cuboid3DAnnotationView | None = None,
    bounding_box: ObjectDetectionAnnotationView | None = None,
) -> AnnotationView:
    """Builds an annotation view with a cuboid or a bounding box, without a database."""
    return AnnotationView(
        parent_sample_id=uuid.uuid4(),
        sample_id=uuid.uuid4(),
        annotation_collection_id=uuid.uuid4(),
        annotation_type=AnnotationType.CUBOID_3D
        if cuboid is not None
        else AnnotationType.OBJECT_DETECTION,
        annotation_label=AnnotationView.AnnotationLabel(annotation_label_name="truck"),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        cuboid_3d_details=cuboid,
        object_detection_details=bounding_box,
    )
