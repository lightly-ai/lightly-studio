"""Tests for SampleFilter class."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlmodel import Session, col, select

from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_confusion_matrix import ConfusionCell
from lightly_studio.models.image import ImageTable
from lightly_studio.models.query_expr import (
    EqualityComparisonOperator,
    FieldRef,
    IntegerExpr,
    OrdinalComparisonOperator,
    QueryExpr,
    StringExpr,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import (
    caption_resolver,
    evaluation_annotation_metric_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import Metadata
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_images,
    create_tag,
)
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


class TestSampleFilter:
    def test_apply__no_filter(self, db_session: Session) -> None:
        # Create samples
        collection = create_collection(session=db_session)
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
            ],
        )

        # Create the filter
        sample_filter = SampleFilter()

        # Apply the filter
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        # Should return all samples
        assert len(result) == 2
        assert {result[0].sample_id, result[1].sample_id} == {
            samples[0].sample_id,
            samples[1].sample_id,
        }

    def test_apply__sample_id_filter(self, db_session: Session) -> None:
        # Create samples
        collection = create_collection(session=db_session)
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
            ],
        )

        # Create the filter
        filtered_sample_id = samples[1].sample_id
        sample_filter = SampleFilter(sample_ids=[filtered_sample_id])

        # Apply the filter
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        # Should only return one sample
        assert len(result) == 1
        assert result[0].sample_id == filtered_sample_id

    def test_apply__annotations_filter__image_sample(self, db_session: Session) -> None:
        # Create samples
        collection = create_collection(session=db_session)
        collection_id = collection.collection_id
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
            ],
        )

        # Create annotations
        cat_label = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="cat"
        )
        dog_label = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="dog"
        )

        # Add annotations to samples
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=samples[0].sample_id,
            annotation_label_id=cat_label.annotation_label_id,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=samples[1].sample_id,
            annotation_label_id=dog_label.annotation_label_id,
        )

        # Create the filter
        sample_filter = SampleFilter(
            annotations_filter=AnnotationsFilter(
                annotation_label_ids=[dog_label.annotation_label_id]
            )
        )

        # Apply the filter
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        # Should only return samples with dog annotations
        assert len(result) == 1
        assert result[0].sample_id == samples[1].sample_id

    def test_query__annotation_filter_distinct_samples_only(self, db_session: Session) -> None:
        """Test SampleFilter with annotation label filters.

        Samples with multiple annotations of the same label should appear only once.
        """
        # Create samples
        collection = create_collection(session=db_session)
        collection_id = collection.collection_id
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
            ],
        )

        # Create annotation labels
        cat_label = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="cat"
        )
        dog_label = create_annotation_label(
            session=db_session, root_collection_id=collection_id, label_name="dog"
        )

        # Add 2 cat and dog annotations to the first sample
        create_annotations(
            session=db_session,
            collection_id=collection_id,
            annotations=[
                AnnotationDetails(
                    sample_id=samples[0].sample_id,
                    annotation_label_id=cat_label.annotation_label_id,
                ),
                AnnotationDetails(
                    sample_id=samples[0].sample_id,
                    annotation_label_id=cat_label.annotation_label_id,
                ),
                AnnotationDetails(
                    sample_id=samples[0].sample_id,
                    annotation_label_id=dog_label.annotation_label_id,
                ),
                AnnotationDetails(
                    sample_id=samples[0].sample_id,
                    annotation_label_id=dog_label.annotation_label_id,
                ),
            ],
        )

        # Create the filter
        sample_filter = SampleFilter(
            annotations_filter=AnnotationsFilter(
                annotation_label_ids=[cat_label.annotation_label_id, dog_label.annotation_label_id]
            )
        )

        # Apply the filter
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        # Should only return samples[0]
        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_query__tag_filter(self, db_session: Session) -> None:
        # Create samples
        collection = create_collection(session=db_session)
        collection_id = collection.collection_id
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
            ],
        )

        # Create tags
        tag1 = create_tag(
            session=db_session, collection_id=collection_id, tag_name="tag1", kind="sample"
        )
        tag2 = create_tag(
            session=db_session, collection_id=collection_id, tag_name="tag2", kind="sample"
        )

        # Add samples to tags
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=tag1.tag_id,
            sample_ids=[samples[0].sample_id],
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=tag2.tag_id,
            sample_ids=[samples[1].sample_id],
        )

        # Create the filter
        sample_filter = SampleFilter(tag_ids=[tag1.tag_id])

        # Apply the filter
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        # Should only return samples[0]
        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_query__tag_filter_distinct_samples_only(
        self,
        db_session: Session,
    ) -> None:
        """Test SampleFilter with tag filters.

        Samples with multiple identical tags should appear only once.
        """
        collection = create_collection(session=db_session)
        collection_id = collection.collection_id
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
            ],
        )

        # Create tags
        tag1 = create_tag(
            session=db_session, collection_id=collection_id, tag_name="tag1", kind="sample"
        )
        tag2 = create_tag(
            session=db_session, collection_id=collection_id, tag_name="tag2", kind="sample"
        )

        # Add tag1 and tag2 twice to the first sample
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=tag1.tag_id,
            sample_ids=[samples[0].sample_id],
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=tag1.tag_id,
            sample_ids=[samples[0].sample_id],
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=tag2.tag_id,
            sample_ids=[samples[0].sample_id],
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=tag2.tag_id,
            sample_ids=[samples[0].sample_id],
        )

        # Create the filter with tag1
        sample_filter = SampleFilter(tag_ids=[tag1.tag_id, tag2.tag_id])

        # Apply the filter
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        # Should return samples[0]
        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_query__metadata_filter(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
            ],
        )

        # Create metadata
        samples[0].sample["height"] = 100
        samples[1].sample["height"] = 200

        # Create the filter
        sample_filter = SampleFilter(metadata_filters=[Metadata("height") > 150])

        # Apply the filter
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        # Should return samples[1]
        assert len(result) == 1
        assert result[0].sample_id == samples[1].sample_id

    def test_query__has_captions_filter(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
            ],
        )

        # Create multiple captions for samples[0]
        caption_resolver.create_many(
            session=db_session,
            parent_collection_id=collection.collection_id,
            captions=[
                CaptionCreate(
                    parent_sample_id=samples[0].sample_id,
                    text="caption 1",
                ),
                CaptionCreate(
                    parent_sample_id=samples[0].sample_id,
                    text="caption 2",
                ),
            ],
        )

        base_query = select(SampleTable).where(
            col(SampleTable.collection_id) == collection.collection_id
        )

        # Create a positive filter
        sample_filter = SampleFilter(has_captions=True)
        filtered_query = sample_filter.apply(query=base_query)
        result = db_session.exec(filtered_query).all()

        # Should return samples[0]
        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

        # Create a negative filter
        sample_filter = SampleFilter(has_captions=False)
        filtered_query = sample_filter.apply(query=base_query)
        result = db_session.exec(filtered_query).all()

        # Should return samples[1]
        assert len(result) == 1
        assert result[0].sample_id == samples[1].sample_id

    def test_apply__query_expr_filter(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path="a.png"), ImageStub(path="b.png")],
        )

        sample_filter = SampleFilter(
            query_expr=QueryExpr(
                match_expr=StringExpr(
                    field=FieldRef(table="image", name="file_name"),
                    operator=EqualityComparisonOperator.EQ,
                    value="b.png",
                )
            )
        )

        query = select(ImageTable).join(ImageTable.sample)
        filtered_query = sample_filter.apply(query=query)
        result = db_session.exec(filtered_query).all()

        assert len(result) == 1
        assert result[0].sample_id == samples[1].sample_id

    def test_query__combination(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        collection_id = collection.collection_id
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="sample_0.png"),
                ImageStub(path="sample_1.png"),
                ImageStub(path="sample_2.png"),
                ImageStub(path="sample_3.png"),
            ],
        )

        # Sample ids for samples 0, 1, 2
        sample_ids = [samples[0].sample_id, samples[1].sample_id, samples[2].sample_id]

        # Tag samples
        # Add tag1 to samples 1, 2 and tag2 to samples 0, 1
        tag1 = create_tag(
            session=db_session, collection_id=collection_id, tag_name="tag1", kind="sample"
        )
        tag2 = create_tag(
            session=db_session, collection_id=collection_id, tag_name="tag2", kind="sample"
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=tag1.tag_id,
            sample_ids=[samples[1].sample_id, samples[2].sample_id],
        )
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session,
            tag_id=tag2.tag_id,
            sample_ids=[samples[0].sample_id, samples[1].sample_id],
        )

        # Create metadata for samples 1, 2, 3
        samples[1].sample["height"] = 100
        samples[2].sample["height"] = 200
        samples[3].sample["height"] = 300

        # Create the filter
        sample_filter = SampleFilter(
            sample_ids=sample_ids,
            annotation_label_ids=None,
            tag_ids=[tag1.tag_id],
            metadata_filters=[Metadata("height") < 250],
        )

        # Apply the filter
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        # Should return samples 1 and 2
        assert len(result) == 2
        assert {result[0].sample_id, result[1].sample_id} == {
            samples[1].sample_id,
            samples[2].sample_id,
        }

    def test_apply__region_sample_ids__none_applies_no_restriction(
        self, db_session: Session
    ) -> None:
        collection = create_collection(session=db_session)
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path="sample_0.png"), ImageStub(path="sample_1.png")],
        )

        sample_filter = SampleFilter(region_sample_ids=None)
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        assert {sample.sample_id for sample in result} == {
            samples[0].sample_id,
            samples[1].sample_id,
        }

    def test_apply__region_sample_ids__empty_matches_nothing(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path="sample_0.png")],
        )

        sample_filter = SampleFilter(region_sample_ids=[])
        filtered_query = sample_filter.apply(query=select(SampleTable))

        assert db_session.exec(filtered_query).all() == []

    def test_apply__region_sample_ids__restricts_to_ids(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[ImageStub(path="sample_0.png"), ImageStub(path="sample_1.png")],
        )

        sample_filter = SampleFilter(region_sample_ids=[samples[0].sample_id])
        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        assert [sample.sample_id for sample in result] == [samples[0].sample_id]

    def test_apply__combination_with_query_expr(self, db_session: Session) -> None:
        collection = create_collection(session=db_session)
        samples = create_images(
            db_session=db_session,
            collection_id=collection.collection_id,
            images=[
                ImageStub(path="a.png", width=800),
                ImageStub(path="b.png", width=800),
                ImageStub(path="c.png", width=200),
            ],
        )

        # query_expr matches samples[0] and samples[1] (width > 500)
        # sample_ids restricts to samples[1] and samples[2]
        # AND gives only samples[1]
        sample_filter = SampleFilter(
            sample_ids=[samples[1].sample_id, samples[2].sample_id],
            query_expr=QueryExpr(
                match_expr=IntegerExpr(
                    field=FieldRef(table="image", name="width"),
                    operator=OrdinalComparisonOperator.GT,
                    value=500,
                )
            ),
        )

        query = select(ImageTable).join(ImageTable.sample)
        filtered_query = sample_filter.apply(query=query)
        result = db_session.exec(filtered_query).all()

        assert len(result) == 1
        assert result[0].sample_id == samples[1].sample_id


class TestSampleFilterConfusionCell:
    def test_apply__confusion_cell__returns_only_matching_pairing(
        self, db_session: Session
    ) -> None:
        dataset = create_collection(session=db_session)
        dataset_id = dataset.collection_id
        run = evaluation_sample_metric_helpers.create_run(
            session=db_session, collection_id=dataset_id
        )
        samples = create_images(
            db_session=db_session,
            collection_id=dataset_id,
            images=[
                ImageStub(path="car_truck.png"),
                ImageStub(path="person_person.png"),
                ImageStub(path="car_person.png"),
            ],
        )
        car = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="car"
        )
        truck = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="truck"
        )
        person = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="person"
        )
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[0],
            labels=(car, truck),
        )
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[1],
            labels=(person, person),
        )
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[2],
            labels=(car, person),
        )

        sample_filter = SampleFilter(
            confusion_cell=ConfusionCell(
                evaluation_run_id=run.id, gt_label="car", pred_label="truck"
            )
        )

        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_apply__confusion_cell__scopes_to_evaluation_run(self, db_session: Session) -> None:
        dataset = create_collection(session=db_session)
        dataset_id = dataset.collection_id
        run_a = evaluation_sample_metric_helpers.create_run(
            session=db_session, collection_id=dataset_id, name="run_a"
        )
        run_b = evaluation_sample_metric_helpers.create_run(
            session=db_session, collection_id=dataset_id, name="run_b"
        )
        samples = create_images(
            db_session=db_session,
            collection_id=dataset_id,
            images=[
                ImageStub(path="run_a_sample.png"),
                ImageStub(path="run_b_sample.png"),
            ],
        )
        car = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="car"
        )
        truck = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="truck"
        )
        # Same car -> truck pairing recorded in two different runs.
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run_a.id,
            image=samples[0],
            labels=(car, truck),
        )
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run_b.id,
            image=samples[1],
            labels=(car, truck),
        )

        sample_filter = SampleFilter(
            confusion_cell=ConfusionCell(
                evaluation_run_id=run_a.id, gt_label="car", pred_label="truck"
            )
        )

        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_apply__confusion_cell__ands_with_other_predicate(self, db_session: Session) -> None:
        dataset = create_collection(session=db_session)
        dataset_id = dataset.collection_id
        run = evaluation_sample_metric_helpers.create_run(
            session=db_session, collection_id=dataset_id
        )
        samples = create_images(
            db_session=db_session,
            collection_id=dataset_id,
            images=[
                ImageStub(path="car_truck_0.png"),
                ImageStub(path="car_truck_1.png"),
            ],
        )
        car = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="car"
        )
        truck = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="truck"
        )
        # Both samples share the car -> truck pairing.
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[0],
            labels=(car, truck),
        )
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[1],
            labels=(car, truck),
        )

        # ANDing with a sample_ids predicate narrows the cell to a single sample.
        sample_filter = SampleFilter(
            confusion_cell=ConfusionCell(
                evaluation_run_id=run.id, gt_label="car", pred_label="truck"
            ),
            sample_ids=[samples[1].sample_id],
        )

        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        assert len(result) == 1
        assert result[0].sample_id == samples[1].sample_id

    def test_apply__confusion_cell__false_positive_bucket(self, db_session: Session) -> None:
        # gt_label=None selects predictions with no matching ground truth.
        dataset = create_collection(session=db_session)
        dataset_id = dataset.collection_id
        run = evaluation_sample_metric_helpers.create_run(
            session=db_session, collection_id=dataset_id
        )
        samples = create_images(
            db_session=db_session,
            collection_id=dataset_id,
            images=[
                ImageStub(path="fp_truck.png"),
                ImageStub(path="fp_car.png"),
                ImageStub(path="tp_truck.png"),
            ],
        )
        truck = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="truck"
        )
        car = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="car"
        )
        # A spurious truck (FP), a spurious car (FP), and a correctly paired truck (TP).
        _seed_false_positive(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[0],
            label=truck,
        )
        _seed_false_positive(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[1],
            label=car,
        )
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[2],
            labels=(truck, truck),
        )

        sample_filter = SampleFilter(
            confusion_cell=ConfusionCell(
                evaluation_run_id=run.id, gt_label=None, pred_label="truck"
            )
        )

        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_apply__confusion_cell__false_negative_bucket(self, db_session: Session) -> None:
        # pred_label=None selects ground truths with no matching prediction.
        dataset = create_collection(session=db_session)
        dataset_id = dataset.collection_id
        run = evaluation_sample_metric_helpers.create_run(
            session=db_session, collection_id=dataset_id
        )
        samples = create_images(
            db_session=db_session,
            collection_id=dataset_id,
            images=[
                ImageStub(path="fn_car.png"),
                ImageStub(path="fn_truck.png"),
                ImageStub(path="tp_car.png"),
            ],
        )
        car = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="car"
        )
        truck = create_annotation_label(
            session=db_session, root_collection_id=dataset_id, label_name="truck"
        )
        # A missed car (FN), a missed truck (FN), and a correctly paired car (TP).
        _seed_false_negative(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[0],
            label=car,
        )
        _seed_false_negative(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[1],
            label=truck,
        )
        _seed_pair(
            session=db_session,
            dataset_id=dataset_id,
            run_id=run.id,
            image=samples[2],
            labels=(car, car),
        )

        sample_filter = SampleFilter(
            confusion_cell=ConfusionCell(evaluation_run_id=run.id, gt_label="car", pred_label=None)
        )

        filtered_query = sample_filter.apply(query=select(SampleTable))
        result = db_session.exec(filtered_query).all()

        assert len(result) == 1
        assert result[0].sample_id == samples[0].sample_id

    def test_confusion_cell__rejects_both_labels_null(self) -> None:
        with pytest.raises(ValidationError):
            ConfusionCell(evaluation_run_id=uuid4(), gt_label=None, pred_label=None)


def _seed_pair(
    session: Session,
    dataset_id: UUID,
    run_id: UUID,
    image: ImageTable,
    labels: tuple[AnnotationLabelTable, AnnotationLabelTable],
) -> None:
    """Attach a gt/pred annotation pair to ``image`` and persist a metric row for it."""
    gt_label, pred_label = labels
    gt_annotation = create_annotation(
        session=session,
        collection_id=dataset_id,
        sample_id=image.sample_id,
        annotation_label_id=gt_label.annotation_label_id,
    )
    pred_annotation = create_annotation(
        session=session,
        collection_id=dataset_id,
        sample_id=image.sample_id,
        annotation_label_id=pred_label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                pred_annotation_id=pred_annotation.sample_id,
                metric_name="iou",
                value=0.9,
            )
        ],
    )


def _seed_false_positive(
    session: Session,
    dataset_id: UUID,
    run_id: UUID,
    image: ImageTable,
    label: AnnotationLabelTable,
) -> None:
    """Persist a false-positive metric row (prediction with no matching ground truth)."""
    pred_annotation = create_annotation(
        session=session,
        collection_id=dataset_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_id,
                sample_id=image.sample_id,
                gt_annotation_id=None,
                pred_annotation_id=pred_annotation.sample_id,
            )
        ],
    )


def _seed_false_negative(
    session: Session,
    dataset_id: UUID,
    run_id: UUID,
    image: ImageTable,
    label: AnnotationLabelTable,
) -> None:
    """Persist a false-negative metric row (ground truth with no matching prediction)."""
    gt_annotation = create_annotation(
        session=session,
        collection_id=dataset_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    evaluation_annotation_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_id,
                sample_id=image.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                pred_annotation_id=None,
            )
        ],
    )
