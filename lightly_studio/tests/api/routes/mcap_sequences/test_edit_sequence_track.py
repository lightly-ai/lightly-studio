"""Track editing creates authored endpoints and generated intermediate cuboids."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import annotation_resolver, group_resolver
from tests.helpers_resolvers import create_annotation_label, cuboid_create
from tests.resolvers.mcap_group_sequence_resolver import helpers


@pytest.mark.parametrize(("mode", "expected_px"), [("interpolate", 4), ("hold", 0)])
def test_start_and_extend_track(
    test_client: TestClient, db_session: Session, mode: str, expected_px: float
) -> None:
    """The two endpoint cuboids stay authored and the middle tick gets interpolation."""
    fixture = helpers.create_mcap_sequence(session=db_session)
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        groups=[set(), set(), set()],
    )
    for group_id, seq_number in zip(group_ids, [2, 5, 9]):
        db_session.add(
            SampleSequenceLinkTable(
                sample_id=group_id,
                sequence_sample_id=fixture.sample_id,
                seq_number=seq_number,
            )
        )
    db_session.commit()
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
                parent_sample_id=group_ids[0],
                annotation_label_id=label.annotation_label_id,
                px=0,
            ),
            cuboid_create(
                parent_sample_id=group_ids[2],
                annotation_label_id=label.annotation_label_id,
                px=8,
            ),
        ],
        collection_name="ground_truth",
    )
    base = (
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/tracks"
    )

    started = test_client.post(base, json={"annotation_id": str(annotation_ids[0])})
    assert started.status_code == 200, started.text
    track_id = started.json()["object_track_id"]
    assert started.json()["managed"] is True
    extended = test_client.post(
        f"{base}/{track_id}/keyframes",
        json={"annotation_id": str(annotation_ids[1]), "mode": mode},
    )
    assert extended.status_code == 200, extended.text
    rows = test_client.get(base).json()["tracks"][0]
    assert rows["managed"] is True
    assert [(row["seq_number"], row["interpolated"]) for row in rows["annotations"]] == [
        (2, False),
        (5, True),
        (9, False),
    ]
    middle_id = rows["annotations"][1]["annotation_id"]
    middle = db_session.get(Cuboid3DAnnotationTable, middle_id)
    assert middle is not None
    assert middle.px == expected_px
    assert db_session.get(AnnotationBaseTable, middle_id).object_track_id == UUID(track_id)

    repeated = test_client.post(
        f"{base}/{track_id}/keyframes",
        json={"annotation_id": str(annotation_ids[1]), "mode": mode},
    )
    assert repeated.status_code == 200
    assert test_client.get(base).json()["tracks"][0]["annotations"] == rows["annotations"]
