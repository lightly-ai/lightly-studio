from __future__ import annotations

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.assisted_labeling.fake_provider import FakeProvider
from lightly_studio.models.assisted_labeling import (
    AnnotationBox,
    AnnotationPoint,
    AnnotationPreviewBox,
    InteractiveAnnotationRequest,
)
from lightly_studio.services import assisted_labeling_service
from tests.helpers_resolvers import create_collection, create_image
from tests.services.assisted_labeling_service import helpers


def test_create_interactive_preview__points(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    response = assisted_labeling_service.create_interactive_preview(
        session=db_session,
        request=InteractiveAnnotationRequest(
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            points=[AnnotationPoint(x=0.5, y=0.5, positive=True)],
        ),
    )

    # The fake provider returns a disk with radius 5 around the pixel (50, 25).
    assert response.prediction is not None
    assert response.prediction.bbox == AnnotationPreviewBox(x=45, y=20, width=11, height=11)
    assert response.prediction.score == 0.9
    assert response.prediction.class_name is None
    assert response.latency_ms >= 0


def test_create_interactive_preview__boxes(db_session: Session) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    response = assisted_labeling_service.create_interactive_preview(
        session=db_session,
        request=InteractiveAnnotationRequest(
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            boxes=[AnnotationBox(x=0.1, y=0.2, width=0.4, height=0.6)],
        ),
    )

    # The fake provider returns an ellipse inside the pixel box (10, 10, 50, 40).
    assert response.prediction is not None
    assert response.prediction.bbox == AnnotationPreviewBox(x=10, y=10, width=41, height=31)


def test_create_interactive_preview__no_mask(db_session: Session, mocker: MockerFixture) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    mocker.patch.object(FakeProvider, "segment", return_value=[])
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    response = assisted_labeling_service.create_interactive_preview(
        session=db_session,
        request=InteractiveAnnotationRequest(
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            points=[AnnotationPoint(x=0.5, y=0.5, positive=True)],
        ),
    )

    assert response.prediction is None


def test_create_interactive_preview__prompt(db_session: Session, mocker: MockerFixture) -> None:
    helpers.select_provider(session=db_session, provider_id="fake")
    spy_segment = mocker.spy(FakeProvider, "segment")
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=100, height=50
    )

    assisted_labeling_service.create_interactive_preview(
        session=db_session,
        request=InteractiveAnnotationRequest(
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            points=[
                AnnotationPoint(x=0.5, y=0.5, positive=True),
                AnnotationPoint(x=0.1, y=0.2, positive=False),
            ],
        ),
    )

    prompt = spy_segment.call_args.kwargs["prompt"]
    assert [(point.x, point.y, point.positive) for point in prompt.points] == [
        (50, 25, True),
        (10, 10, False),
    ]
    assert prompt.boxes == []
    assert prompt.text is None
    assert prompt.max_masks == 1
