"""Tests for SampleFilter class."""

from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.caption import CaptionCreate
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
from lightly_studio.resolvers import caption_resolver, tag_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import Metadata
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_images,
    create_tag,
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
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=samples[0].sample_id,
            annotation_label_id=cat_label.annotation_label_id,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=samples[0].sample_id,
            annotation_label_id=cat_label.annotation_label_id,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=samples[0].sample_id,
            annotation_label_id=dog_label.annotation_label_id,
        )
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=samples[0].sample_id,
            annotation_label_id=dog_label.annotation_label_id,
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
