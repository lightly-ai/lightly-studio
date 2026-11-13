from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.errors import AnnotationSourceInUseError, NotFoundError
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    caption_resolver,
    collection_embedding_model_resolver,
    collection_resolver,
    evaluation_run_resolver,
    export_job_resolver,
)
from lightly_studio.services import annotation_source_service
from tests.helpers_resolvers import (
    create_caption,
    create_collection,
    create_embedding_model,
    create_image,
    create_source_annotations,
)


def test_delete_annotation_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (gt,) = create_source_annotations(
        session=db_session, image=image, source_name="ground_truth", count=1
    )
    pred = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=2
    )
    pred_source_id = pred[0].annotation_collection_id
    create_embedding_model(session=db_session, collection_id=pred_source_id, set_as_default=True)

    deleted_count = annotation_source_service.delete_annotation_source(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_source_id=pred_source_id,
    )

    assert deleted_count == 2
    assert collection_resolver.get_by_id(session=db_session, collection_id=pred_source_id) is None
    assert (
        annotation_collection_coverage_resolver.list_by_collection_id(
            session=db_session, annotation_collection_id=pred_source_id
        )
        == []
    )
    assert (
        collection_embedding_model_resolver.get_all_by_collection_id(
            session=db_session, collection_id=pred_source_id
        )
        == []
    )
    remaining = annotation_resolver.get_all_by_parent_sample_ids(
        session=db_session, parent_sample_ids=[image.sample_id]
    )
    assert [annotation.sample_id for annotation in remaining] == [gt.sample_id]


def test_delete_annotation_source__empty_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )
    pred_source_id = pred.annotation_collection_id
    annotation_resolver.delete_annotations_by_ids(
        session=db_session, annotation_ids=[pred.sample_id]
    )

    deleted_count = annotation_source_service.delete_annotation_source(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_source_id=pred_source_id,
    )

    assert deleted_count == 0
    assert collection_resolver.get_by_id(session=db_session, collection_id=pred_source_id) is None


def test_delete_annotation_source__other_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    other_collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )

    with pytest.raises(NotFoundError, match="not found"):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=other_collection.collection_id,
            annotation_source_id=pred.annotation_collection_id,
        )


def test_delete_annotation_source__not_an_annotation_source(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    with pytest.raises(NotFoundError, match="not found"):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=collection.collection_id,
        )


def test_delete_annotation_source__used_by_evaluation_run(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (gt,) = create_source_annotations(
        session=db_session, image=image, source_name="ground_truth", count=1
    )
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )
    evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_a",
            gt_annotation_collection_id=gt.annotation_collection_id,
            pred_annotation_collection_id=pred.annotation_collection_id,
            dataset_id=collection.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )

    with pytest.raises(
        AnnotationSourceInUseError,
        match=r"'predictions' is used by the evaluation runs run_a\. Delete these",
    ):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=pred.annotation_collection_id,
        )
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=pred.sample_id)


def test_delete_annotation_source__has_child_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )
    create_collection(
        session=db_session,
        collection_name="crops",
        parent_collection_id=pred.annotation_collection_id,
        sample_type=SampleType.IMAGE,
    )

    with pytest.raises(
        AnnotationSourceInUseError,
        match=r"'predictions' cannot be deleted because it has data attached: crops\.",
    ):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=pred.annotation_collection_id,
        )
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=pred.sample_id)


def test_delete_annotation_source__exported(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )
    export_job_resolver.create(
        session=db_session,
        collection_id=pred.annotation_collection_id,
        export_path="/tmp/predictions.json",
    )

    with pytest.raises(AnnotationSourceInUseError, match="it was exported"):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=pred.annotation_collection_id,
        )
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=pred.sample_id)


def test_delete_annotation_source__exported_caption(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )
    caption = create_caption(
        session=db_session,
        collection_id=pred.annotation_collection_id,
        parent_sample_id=pred.sample_id,
    )
    export_job_resolver.create(
        session=db_session,
        collection_id=caption.sample.collection_id,
        export_path="/tmp/captions.json",
    )

    with pytest.raises(AnnotationSourceInUseError, match="it was exported"):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=pred.annotation_collection_id,
        )
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=pred.sample_id)


def test_delete_annotation_source__caption_with_caption(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )
    caption = create_caption(
        session=db_session,
        collection_id=pred.annotation_collection_id,
        parent_sample_id=pred.sample_id,
    )
    create_caption(
        session=db_session,
        collection_id=caption.sample.collection_id,
        parent_sample_id=caption.sample_id,
    )

    with pytest.raises(
        AnnotationSourceInUseError,
        match=r"'predictions' cannot be deleted because it has data attached: caption\.",
    ):
        annotation_source_service.delete_annotation_source(
            session=db_session,
            dataset_collection_id=collection.collection_id,
            annotation_source_id=pred.annotation_collection_id,
        )
    assert annotation_resolver.get_by_id(session=db_session, annotation_id=pred.sample_id)


def test_delete_annotation_source__with_caption(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )
    source_id = pred.annotation_collection_id
    caption = create_caption(
        session=db_session, collection_id=source_id, parent_sample_id=pred.sample_id
    )
    caption_sample_id = caption.sample_id
    caption_collection_id = caption.sample.collection_id

    deleted_count = annotation_source_service.delete_annotation_source(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_source_id=source_id,
    )

    assert deleted_count == 1
    assert caption_resolver.get_by_ids(session=db_session, sample_ids=[caption_sample_id]) == []
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=caption_collection_id)
        is None
    )
    assert collection_resolver.get_by_id(session=db_session, collection_id=source_id) is None


def test_delete_annotation_source__deleted_caption(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    (pred,) = create_source_annotations(
        session=db_session, image=image, source_name="predictions", count=1
    )
    source_id = pred.annotation_collection_id
    # The delete of a caption keeps its sample in the caption collection.
    caption = create_caption(
        session=db_session, collection_id=source_id, parent_sample_id=pred.sample_id
    )
    caption_collection_id = caption.sample.collection_id
    caption_resolver.delete_caption(session=db_session, sample_id=caption.sample_id)

    deleted_count = annotation_source_service.delete_annotation_source(
        session=db_session,
        dataset_collection_id=collection.collection_id,
        annotation_source_id=source_id,
    )

    assert deleted_count == 1
    assert (
        collection_resolver.get_by_id(session=db_session, collection_id=caption_collection_id)
        is None
    )
    assert collection_resolver.get_by_id(session=db_session, collection_id=source_id) is None
