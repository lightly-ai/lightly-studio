"""Tests for the sequence-scoped track timeline route."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import (
    annotation_resolver,
    group_resolver,
    mcap_group_sequence_resolver,
    object_track_resolver,
)
from tests.helpers_resolvers import create_annotation_label, cuboid_create
from tests.resolvers.mcap_group_sequence_resolver import helpers


def test_get_sequence_tracks__sparse_ticks_and_gap(
    test_client: TestClient, db_session: Session
) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set(), set(), set(), set()],
    )
    for group_id, seq_number in zip(group_ids, [2, 5, 9, 12]):
        db_session.add(
            SampleSequenceLinkTable(
                sample_id=group_id,
                sequence_sample_id=fixture.sample_id,
                seq_number=seq_number,
            )
        )
    db_session.commit()
    track_id = object_track_resolver.create_many(
        session=db_session,
        tracks=[
            ObjectTrackCreate(
                object_track_number=7,
                dataset_id=fixture.sequence_collection.dataset_id,
            )
        ],
    )[0]
    label = create_annotation_label(
        session=db_session,
        root_collection_id=fixture.group_collection.collection_id,
        label_name="truck",
    )
    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=fixture.group_collection.collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=group_ids[index],
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
            )
            for index in [0, 1, 3]
        ],
        collection_name="ground_truth",
    )
    generated = db_session.get(Cuboid3DAnnotationTable, annotation_ids[1])
    assert generated is not None
    generated.interpolated = True
    db_session.commit()
    other_sequence_id = mcap_group_sequence_resolver.create(
        session=db_session,
        collection_id=fixture.sequence_collection.collection_id,
        recording_id=fixture.recording_id,
    )
    other_group_id = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set()],
    )[0]
    db_session.add(
        SampleSequenceLinkTable(
            sample_id=other_group_id,
            sequence_sample_id=other_sequence_id,
            seq_number=20,
        )
    )
    db_session.commit()
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=fixture.group_collection.collection_id,
        annotations=[
            cuboid_create(
                parent_sample_id=other_group_id,
                annotation_label_id=label.annotation_label_id,
                object_track_id=track_id,
            )
        ],
        collection_name="ground_truth",
    )

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/tracks"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "tracks": [
            {
                "object_track_id": str(track_id),
                "object_track_number": 7,
                "annotations": [
                    {
                        "seq_number": 2,
                        "annotation_id": str(annotation_ids[0]),
                        "interpolated": False,
                    },
                    {
                        "seq_number": 5,
                        "annotation_id": str(annotation_ids[1]),
                        "interpolated": True,
                    },
                    {
                        "seq_number": 12,
                        "annotation_id": str(annotation_ids[2]),
                        "interpolated": False,
                    },
                ],
            }
        ]
    }


def test_get_sequence_tracks__empty_and_wrong_dataset(
    test_client: TestClient, db_session: Session
) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    url = (
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/tracks"
    )

    assert test_client.get(url).json() == {"tracks": []}
    assert test_client.get(url).status_code == HTTP_STATUS_OK
    assert (
        test_client.get(
            f"/datasets/{uuid.uuid4()}/mcap-sequences/{fixture.sample_id}/tracks"
        ).status_code
        == HTTP_STATUS_NOT_FOUND
    )
