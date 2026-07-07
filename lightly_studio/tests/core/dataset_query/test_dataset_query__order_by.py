from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByEvaluationMetricField, OrderByField
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import (
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


class TestDatasetQueryOrderBy:
    def test_order_by__ascending_by_file_name(self, db_session: Session) -> None:
        """Test ordering samples by file name in ascending order."""
        # Arrange
        dataset = create_collection(session=db_session)
        image1 = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/zebra.jpg",
            width=100,
            height=100,
        )
        image2 = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/alpha.jpg",
            width=200,
            height=200,
        )

        # Act
        query = DatasetQuery(dataset=dataset, session=db_session)
        result_samples = query.order_by(OrderByField(ImageSampleField.file_name)).to_list()

        # Assert
        assert len(result_samples) == 2
        # Should be ordered alphabetically: alpha.jpg, zebra.jpg
        assert result_samples[0].sample_id == image2.sample_id  # alpha.jpg
        assert result_samples[1].sample_id == image1.sample_id  # zebra.jpg

    def test_order_by__triple_criteria_width_height_file_name(self, db_session: Session) -> None:
        """Test ordering by triple criteria: width asc, height desc, file_name asc."""
        # Arrange
        dataset = create_collection(session=db_session)
        image1 = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/E.jpg",
            width=100,  # Same width as sample2 and sample4
            height=150,
        )
        image2 = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/A.jpg",
            width=100,  # Same width as sample1 and sample4
            height=200,
        )
        image3 = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/B.jpg",
            width=200,  # Same width as sample5
            height=300,  # Same height as sample5 to test file_name ordering
        )
        image4 = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/C.jpg",
            width=100,  # Same width as sample1 and sample2
            height=100,  # Smallest height
        )
        image5 = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/D.jpg",
            width=200,  # Same width as sample3
            height=300,  # Same height as sample3 to test file_name ordering
        )

        # Act: Triple criteria ordering (width asc, height desc, file_name asc)
        query = DatasetQuery(dataset=dataset, session=db_session)
        result_samples = query.order_by(
            OrderByField(ImageSampleField.width),
            OrderByField(ImageSampleField.height).desc(),
            OrderByField(ImageSampleField.file_name).desc().asc(),
        ).to_list()

        # Assert
        assert len(result_samples) == 5
        # Expected order: width=100 by height desc (A=200, E=150, C=100),
        # width=200 by height desc, then by file_name asc (B=300, D=300)
        assert result_samples[0].sample_id == image2.sample_id  # A.jpg, width=100, height=200
        assert result_samples[1].sample_id == image1.sample_id  # E.jpg, width=100, height=150
        assert result_samples[2].sample_id == image4.sample_id  # C.jpg, width=100, height=100
        assert result_samples[3].sample_id == image3.sample_id  # B.jpg, width=200, height=300
        assert result_samples[4].sample_id == image5.sample_id  # D.jpg, width=200, height=300

    def test_order_by__multiple_calls_raises_error(self, db_session: Session) -> None:
        """Test that calling order_by() twice raises ValueError."""
        # Arrange
        dataset = create_collection(session=db_session)
        query = DatasetQuery(dataset=dataset, session=db_session)
        query.order_by(OrderByField(ImageSampleField.file_name))

        # Act & Assert
        with pytest.raises(
            ValueError, match="order_by\\(\\) can only be called once per DatasetQuery instance"
        ):
            query.order_by(OrderByField(ImageSampleField.file_name).desc())

    def test_order_by__evaluation_metric_scopes_run_name_to_dataset(
        self, db_session: Session
    ) -> None:
        """Test ordering by evaluation metric when another dataset has a run with same name."""
        dataset = create_collection(session=db_session)
        image_a = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/a.jpg",
        )
        image_b = create_image(
            session=db_session,
            collection_id=dataset.collection_id,
            file_path_abs="/path/to/b.jpg",
        )
        gt_collection = create_collection(
            session=db_session,
            parent_collection_id=dataset.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
        pred_collection = create_collection(
            session=db_session,
            parent_collection_id=dataset.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
        run = evaluation_run_resolver.create(
            session=db_session,
            evaluation_run_input=EvaluationRunCreate(
                name="run1",
                gt_annotation_collection_id=gt_collection.collection_id,
                dataset_id=gt_collection.dataset_id,
                pred_annotation_collection_id=pred_collection.collection_id,
                task_type=EvaluationTaskType.OBJECT_DETECTION,
            ),
        )

        other_dataset = create_collection(session=db_session)
        other_image = create_image(
            session=db_session,
            collection_id=other_dataset.collection_id,
            file_path_abs="/path/to/other.jpg",
        )
        other_gt_collection = create_collection(
            session=db_session,
            parent_collection_id=other_dataset.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
        other_pred_collection = create_collection(
            session=db_session,
            parent_collection_id=other_dataset.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
        other_run = evaluation_run_resolver.create(
            session=db_session,
            evaluation_run_input=EvaluationRunCreate(
                name="run1",
                gt_annotation_collection_id=other_gt_collection.collection_id,
                dataset_id=other_gt_collection.dataset_id,
                pred_annotation_collection_id=other_pred_collection.collection_id,
                task_type=EvaluationTaskType.OBJECT_DETECTION,
            ),
        )
        evaluation_sample_metric_resolver.create_many(
            session=db_session,
            records=[
                EvaluationSampleMetricCreate(
                    evaluation_run_id=run.id,
                    sample_id=image_a.sample_id,
                    metric_name="score",
                    value=0.9,
                ),
                EvaluationSampleMetricCreate(
                    evaluation_run_id=run.id,
                    sample_id=image_b.sample_id,
                    metric_name="score",
                    value=0.1,
                ),
                EvaluationSampleMetricCreate(
                    evaluation_run_id=other_run.id,
                    sample_id=other_image.sample_id,
                    metric_name="score",
                    value=0.0,
                ),
            ],
        )

        result_samples = (
            DatasetQuery(dataset=dataset, session=db_session)
            .order_by(OrderByEvaluationMetricField("run1", "score"))
            .to_list()
        )

        assert [sample.sample_id for sample in result_samples] == [
            image_b.sample_id,
            image_a.sample_id,
        ]
