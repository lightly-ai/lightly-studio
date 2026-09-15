"""Bulk-insert sensor calibrations for a recording."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.mcap_group_component_definition import (
    McapDataType,
    McapGroupComponentDefinitionTable,
)
from lightly_studio.models.recording import RecordingTable
from lightly_studio.models.sensor_calibration import (
    SensorCalibrationCreate,
    SensorCalibrationTable,
)


def create_many(
    session: Session,
    rows: Sequence[SensorCalibrationCreate],
) -> list[UUID]:
    """Bulk-insert sensor calibration rows for a bag's camera slots.

    Args:
        session: The database session.
        rows: Calibration rows to insert.

    Returns:
        The generated primary keys, in the same order as ``rows``.

    Raises:
        ValueError: If ``rows`` is empty, a referenced ``recording_id`` has no
            ``recording`` row, or a referenced ``collection_id`` is not an MCAP group
            component definition with ``mcap_data_type=video_frame`` (a classic IMAGE
            slot, a point-cloud slot, or an unknown collection all raise).
        sqlalchemy.exc.IntegrityError: If a row duplicates an existing
            ``(recording_id, collection_id)`` pair.
    """
    if not rows:
        raise ValueError("rows must be non-empty.")
    _check_recordings_exist(session=session, recording_ids={row.recording_id for row in rows})
    _check_video_frame_slots(session=session, collection_ids={row.collection_id for row in rows})
    table_rows = [SensorCalibrationTable.model_validate(obj=row) for row in rows]
    session.bulk_save_objects(objects=table_rows)
    session.commit()
    return [row.sensor_calibration_id for row in table_rows]


def _check_recordings_exist(session: Session, recording_ids: set[UUID]) -> None:
    found_ids = set(
        session.exec(
            select(RecordingTable.recording_id).where(
                col(RecordingTable.recording_id).in_(recording_ids)
            )
        ).all()
    )
    for recording_id in recording_ids - found_ids:
        raise ValueError(f"Recording with id {recording_id} not found.")


def _check_video_frame_slots(session: Session, collection_ids: set[UUID]) -> None:
    definitions = session.exec(
        select(McapGroupComponentDefinitionTable).where(
            col(McapGroupComponentDefinitionTable.collection_id).in_(collection_ids)
        )
    ).all()
    by_collection_id = {definition.collection_id: definition for definition in definitions}
    for collection_id in collection_ids:
        definition = by_collection_id.get(collection_id)
        if definition is None:
            raise ValueError(
                f"McapGroupComponentDefinition with collection_id {collection_id} not found."
            )
        if definition.mcap_data_type != McapDataType.VIDEO_FRAME:
            raise ValueError(
                f"collection_id {collection_id} is a '{definition.mcap_data_type.value}' slot; "
                "sensor_calibration requires a 'video_frame' slot."
            )
