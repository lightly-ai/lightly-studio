from __future__ import annotations

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.assisted_labeling.provider import OutputType
from lightly_studio.models.assisted_labeling import (
    AnnotationBox,
    AnnotationPreviewBox,
    InstancesAnnotationRequest,
)
from lightly_studio.services import assisted_labeling_service
from tests.helpers_resolvers import create_collection, create_image
from tests.services.assisted_labeling_service import helpers


def test_create_instances_preview__text(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    response = assisted_labeling_service.create_instances_preview(
        session=db_session,
        request=InstancesAnnotationRequest(
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            prompt=" dog ",
            max_instances=2,
        ),
    )

    # The fake provider returns disks with radius 5 around (25, 25) and (50, 25).
    assert [prediction.bbox for prediction in response.predictions] == [
        AnnotationPreviewBox(x=20, y=20, width=11, height=11),
        AnnotationPreviewBox(x=45, y=20, width=11, height=11),
    ]
    assert [prediction.class_name for prediction in response.predictions] == ["dog", "dog"]
    assert response.latency_ms >= 0


def test_create_instances_preview__prompt(db_session: Session, mocker: MockerFixture) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    spy_segment = mocker.spy(FakeProvider, "segment")
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    assisted_labeling_service.create_instances_preview(
        session=db_session,
        request=InstancesAnnotationRequest(
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            boxes=[AnnotationBox(x=0.1, y=0.2, width=0.4, height=0.6)],
            max_instances=10,
            output_type=OutputType.BOX,
        ),
    )

    # The fake provider supports at most 3 instances.
    prompt = spy_segment.call_args.kwargs["prompt"]
    assert prompt.max_masks == 3
    assert prompt.output_type == OutputType.BOX
    assert prompt.text is None
    assert prompt.points == []
    assert [(box.x_min, box.y_min, box.x_max, box.y_max) for box in prompt.boxes] == [
        (10, 10, 50, 40)
    ]
