from __future__ import annotations

from sqlmodel import Session

from lightly_studio.core.dataset_query import (
    AnnotationEvaluationMetricField,
    AnnotationMetricQuery,
    DatasetQuery,
)
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation_label,
    create_collection,
    create_image,
    create_images,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    AnnotationMetricStub,
    TruePositiveMetricStub,
    create_annotation_metrics,
    create_run,
)


def test_annotation_metric_query__filters_matching_samples(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    [image_a, image_b] = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="/path/to/a.jpg"), ImageStub(path="/path/to/b.jpg")],
    )
    run = create_run(session=db_session, collection_id=collection_id, name="run1")
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    dog_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        annotation_metrics=[
            AnnotationMetricStub(sample_id=image_a.sample_id, metric_name="score", value=0.95),
        ],
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image_a.sample_id,
                metrics={"score": 0.2},
                gt_annotation_label_id=cat_label.annotation_label_id,
                pred_annotation_label_id=dog_label.annotation_label_id,
            ),
            TruePositiveMetricStub(
                sample_id=image_b.sample_id,
                metrics={"score": 0.9},
                gt_annotation_label_id=cat_label.annotation_label_id,
                pred_annotation_label_id=dog_label.annotation_label_id,
            ),
        ],
    )

    results = DatasetQuery(dataset=collection, session=db_session).match(
        AnnotationMetricQuery.confusion(
            "run1",
            "cat",
            "dog",
            AnnotationEvaluationMetricField("score") > 0.5,
        )
    )

    assert [result.sample_id for result in results] == [image_b.sample_id]


def test_annotation_metric_query__scopes_run_name_to_dataset(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    [image_a, image_b] = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="/path/to/a.jpg"), ImageStub(path="/path/to/b.jpg")],
    )
    run = create_run(session=db_session, collection_id=collection_id, name="run1")
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )

    other_dataset = create_collection(session=db_session)
    other_image = create_image(
        session=db_session,
        collection_id=other_dataset.collection_id,
        file_path_abs="/path/to/other.jpg",
    )
    other_run = create_run(
        session=db_session, collection_id=other_dataset.collection_id, name="run1"
    )
    other_label = create_annotation_label(
        session=db_session, root_collection_id=other_dataset.collection_id, label_name="cat"
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image_a.sample_id,
                metrics={"score": 0.9},
                gt_annotation_label_id=cat_label.annotation_label_id,
            ),
            TruePositiveMetricStub(
                sample_id=image_b.sample_id,
                metrics={"score": 0.1},
                gt_annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )
    create_annotation_metrics(
        session=db_session,
        run_id=other_run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=other_image.sample_id,
                metrics={"score": 0.0},
                gt_annotation_label_id=other_label.annotation_label_id,
            ),
        ],
    )

    results = DatasetQuery(dataset=collection, session=db_session).match(
        AnnotationMetricQuery.confusion(
            "run1",
            "cat",
            "cat",
            AnnotationEvaluationMetricField("score") < 0.5,
        )
    )
    assert [result.sample_id for result in results] == [image_b.sample_id]


def test_annotation_metric_query__matches_multiple_metrics(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    [image_a, image_b] = create_images(
        db_session=db_session,
        collection_id=collection_id,
        images=[ImageStub(path="/path/to/a.jpg"), ImageStub(path="/path/to/b.jpg")],
    )
    run = create_run(session=db_session, collection_id=collection_id, name="run1")
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image_a.sample_id,
                gt_annotation_label_id=cat_label.annotation_label_id,
                metrics={"precision": 0.9, "recall": 0.3},
            ),
            TruePositiveMetricStub(
                sample_id=image_b.sample_id,
                gt_annotation_label_id=cat_label.annotation_label_id,
                metrics={"precision": 0.9, "recall": 0.8},
            ),
        ],
    )

    results = DatasetQuery(dataset=collection, session=db_session).match(
        AnnotationMetricQuery.confusion(
            "run1",
            "cat",
            "cat",
            AnnotationEvaluationMetricField("precision") > 0.5,
            AnnotationEvaluationMetricField("recall") > 0.5,
        )
    )
    assert [result.sample_id for result in results] == [image_b.sample_id]


def test_annotation_metric_query__does_not_mix_criteria_across_annotation_pairs(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/a.jpg",
    )
    run = create_run(session=db_session, collection_id=collection.collection_id, name="run1")
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                gt_annotation_label_id=cat_label.annotation_label_id,
                metrics={"precision": 0.9, "recall": 0.3},
            ),
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                gt_annotation_label_id=cat_label.annotation_label_id,
                metrics={"precision": 0.3, "recall": 0.9},
            ),
        ],
    )

    results = DatasetQuery(dataset=collection, session=db_session).match(
        AnnotationMetricQuery.confusion(
            "run1",
            "cat",
            "cat",
            AnnotationEvaluationMetricField("precision") > 0.5,
            AnnotationEvaluationMetricField("recall") > 0.5,
        )
    )

    assert [result.sample_id for result in results] == []


def test_annotation_metric_query__matches_run_without_criteria(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    image_a = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/a.jpg",
    )
    create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/b.jpg",
    )
    run = create_run(session=db_session, collection_id=collection.collection_id, name="run1")
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image_a.sample_id,
                metrics={"score": 0.2},
                gt_annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )

    results = DatasetQuery(dataset=collection, session=db_session).match(
        AnnotationMetricQuery.confusion("run1", "cat", "cat")
    )

    assert [result.sample_id for result in results] == [image_a.sample_id]


def test_annotation_metric_query__matches_off_diagonal_confusion_cell(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/a.jpg",
    )
    run = create_run(session=db_session, collection_id=collection.collection_id, name="run1")
    cat_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="cat",
    )
    dog_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="dog",
    )
    create_annotation_metrics(
        session=db_session,
        run_id=run.id,
        pair_metric_stubs=[
            TruePositiveMetricStub(
                sample_id=image.sample_id,
                metrics={"score": 0.8},
                gt_annotation_label_id=cat_label.annotation_label_id,
                pred_annotation_label_id=dog_label.annotation_label_id,
            ),
        ],
    )

    results = DatasetQuery(dataset=collection, session=db_session).match(
        AnnotationMetricQuery.confusion(run_name="run1", ground_truth="cat", prediction="dog")
    )

    assert [result.sample_id for result in results] == [image.sample_id]
