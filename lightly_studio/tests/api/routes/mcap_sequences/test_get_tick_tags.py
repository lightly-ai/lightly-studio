"""Tests for the MCAP sequence tick-tags route."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import sample_resolver, sequence_resolver, tag_resolver
from tests.helpers_resolvers import create_tag
from tests.resolvers.mcap_group_sequence_resolver import helpers


def test_get_tick_tags(test_client: TestClient, db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)
    tick_sample_ids = sample_resolver.create_many(
        session=db_session,
        samples=[SampleCreate(collection_id=fixture.group_collection.collection_id)] * 3,
    )
    sequence_resolver.add_samples(
        session=db_session,
        sequence_sample_id=fixture.sample_id,
        links=[
            SampleSequenceLinkCreate(sample_id=sample_id, seq_number=seq_number)
            for seq_number, sample_id in enumerate(tick_sample_ids)
        ],
    )
    tag = create_tag(
        session=db_session,
        collection_id=fixture.group_collection.collection_id,
        tag_name="occluded",
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[tick_sample_ids[2], tick_sample_ids[0]]
    )

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/tick-tags"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {
        "tags": [{"tag_id": str(tag.tag_id), "name": "occluded", "seq_numbers": [0, 2]}]
    }


def test_get_tick_tags__no_tags(test_client: TestClient, db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    response = test_client.get(
        f"/datasets/{fixture.sequence_collection.dataset_id}/mcap-sequences/"
        f"{fixture.sample_id}/tick-tags"
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.json() == {"tags": []}


def test_get_tick_tags__unknown_sequence(test_client: TestClient) -> None:
    response = test_client.get(f"/datasets/{uuid.uuid4()}/mcap-sequences/{uuid.uuid4()}/tick-tags")

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def test_get_tick_tags__wrong_dataset(test_client: TestClient, db_session: Session) -> None:
    fixture = helpers.create_mcap_sequence(session=db_session)

    response = test_client.get(
        f"/datasets/{uuid.uuid4()}/mcap-sequences/{fixture.sample_id}/tick-tags"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND
