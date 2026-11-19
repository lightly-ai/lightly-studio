from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlmodel import Session

from lightly_studio.models.unannotated_sample_count import UnannotatedSampleCount
from lightly_studio.models.workflow import WorkflowStatus
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_workflow
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_images,
)


def test_count_unannotated_images(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="car.png"),
            ImageStub(path="unannotated_1.png"),
            ImageStub(path="unannotated_2.png"),
        ],
    )
    car_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[0].sample_id, annotation_label_id=car_label.annotation_label_id
            )
        ],
    )

    count = image_resolver.count_unannotated_images(
        session=db_session,
        collection_id=collection.collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(sample_ids=[images[0].sample_id, images[1].sample_id])
        ),
    )

    assert count == UnannotatedSampleCount(current_count=1, total_count=2)


def test_count_unannotated_images__in_sources(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="in_source_a.png"), ImageStub(path="in_source_b.png")],
    )
    car_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="car"
    )
    source_a = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[0].sample_id, annotation_label_id=car_label.annotation_label_id
            )
        ],
        collection_name="source_a",
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[1].sample_id, annotation_label_id=car_label.annotation_label_id
            )
        ],
        collection_name="source_b",
    )

    count = image_resolver.count_unannotated_images(
        session=db_session,
        collection_id=collection.collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    collection_ids=[source_a[0].annotation_collection_id]
                )
            )
        ),
    )

    assert count == UnannotatedSampleCount(current_count=1, total_count=1)


def test_count_unannotated_images__without_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="unannotated_1.png"), ImageStub(path="unannotated_2.png")],
    )

    count = image_resolver.count_unannotated_images(
        session=db_session, collection_id=collection.collection_id
    )

    assert count == UnannotatedSampleCount(current_count=2, total_count=2)


@pytest.fixture
def workflow_tables(db_session: Session) -> Generator[None, None, None]:
    with helpers_workflow.workflow_tables(session=db_session):
        yield


@pytest.mark.usefixtures("workflow_tables")
def test_count_unannotated_images__workflow_states(db_session: Session) -> None:
    """A workflow status filter restricts the current count to the matching images."""
    collection_id = create_collection(session=db_session).collection_id
    images = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="a.png"), ImageStub(path="b.png"), ImageStub(path="c.png")],
    )
    project_id = helpers_workflow.create_project(session=db_session, dataset_id=collection_id)
    helpers_workflow.add_batch_files(
        session=db_session,
        project_id=project_id,
        states={images[0].sample_id: "in_review", images[1].sample_id: "in_progress"},
    )

    count = image_resolver.count_unannotated_images(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(workflow_states=[WorkflowStatus.IN_REVIEW])
        ),
    )

    assert count == UnannotatedSampleCount(current_count=1, total_count=3)
