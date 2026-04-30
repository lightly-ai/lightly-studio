from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameCreate
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_resolver,
    tag_resolver,
    video_frame_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)
from tests.resolvers.video.helpers import VideoStub, create_videos


@dataclass
class _TestData:
    """Data class to hold test data for annotations."""

    dog_label: AnnotationLabelTable
    cat_label: AnnotationLabelTable
    dog_annotation1: AnnotationBaseTable
    dog_annotation2: AnnotationBaseTable
    cat_annotation: AnnotationBaseTable
    collection: CollectionTable
    sample1: ImageTable
    sample2: ImageTable
    mouse_annotation: AnnotationBaseTable
    collection2: CollectionTable
    sample_with_mouse: ImageTable


@pytest.fixture
def test_data(db_session: Session) -> _TestData:
    """Fixture that provides test database with sample data."""
    collection1 = create_collection(session=db_session)
    collection1_id = collection1.collection_id

    collection2 = create_collection(session=db_session, collection_name="collection2")
    collection2_id = collection2.collection_id

    # Create samples
    image1 = create_image(
        session=db_session, collection_id=collection1_id, file_path_abs="/path/to/sample1.png"
    )
    image2 = create_image(
        session=db_session, collection_id=collection1_id, file_path_abs="/path/to/sample2.png"
    )

    image_with_mouse = create_image(
        session=db_session,
        collection_id=collection2_id,
        file_path_abs="/path/to/sample_with_mouse.png",
    )

    # Create labels
    dog_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection1_id,
        label_name="dog",
    )
    cat_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection1_id,
        label_name="cat",
    )
    mouse_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection2_id,
        label_name="mouse",
    )

    # Create annotations
    dog_annotation1 = create_annotation(
        session=db_session,
        sample_id=image1.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        collection_id=collection1_id,
    )
    dog_annotation2 = create_annotation(
        session=db_session,
        sample_id=image2.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        collection_id=collection1_id,
        annotation_data={
            "segmentation__binary_mask__rle_row_wise": [1, 2, 3],
        },
    )
    cat_annotation = create_annotation(
        session=db_session,
        sample_id=image1.sample_id,
        annotation_label_id=cat_label.annotation_label_id,
        collection_id=collection1_id,
    )
    mouse_annotation = create_annotation(
        session=db_session,
        sample_id=image_with_mouse.sample_id,
        annotation_label_id=mouse_label.annotation_label_id,
        collection_id=collection2_id,
        annotation_data={
            "segmentation__binary_mask__rle_row_wise": [0, 7, 9],
        },
    )

    return _TestData(
        dog_label=dog_label,
        cat_label=cat_label,
        dog_annotation1=dog_annotation1,
        dog_annotation2=dog_annotation2,
        cat_annotation=cat_annotation,
        collection=collection1,
        sample1=image1,
        sample2=image2,
        mouse_annotation=mouse_annotation,
        collection2=collection2,
        sample_with_mouse=image_with_mouse,
    )


def test_create_and_get_annotation(db_session: Session, test_data: _TestData) -> None:
    dog_annotation = test_data.dog_annotation1

    retrieved_annotation = annotation_resolver.get_by_id(
        session=db_session, annotation_id=dog_annotation.sample_id
    )

    assert retrieved_annotation == dog_annotation


def test_create_and_get_annotation__for_video_frame_with_ordering(db_session: Session) -> None:
    collection_id = create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    ).collection_id

    # Create video.
    video_ids = create_videos(
        session=db_session,
        collection_id=collection_id,
        videos=[
            VideoStub(path="/path/to/b_video.mp4"),
            VideoStub(path="/path/to/a_video.mp4"),
        ],
    )
    video_id_b = video_ids[0]
    video_id_a = video_ids[1]
    # Create video frames.
    frames_to_create = [
        VideoFrameCreate(
            frame_number=1,
            frame_timestamp_s=0.1,
            frame_timestamp_pts=1,
            parent_sample_id=video_id_b,
        ),
        VideoFrameCreate(
            frame_number=1,
            frame_timestamp_s=0.1,
            frame_timestamp_pts=1,
            parent_sample_id=video_id_a,
        ),
    ]

    video_frames_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session, collection_id=collection_id, sample_type=SampleType.VIDEO_FRAME
    )
    video_frame_ids = video_frame_resolver.create_many(
        session=db_session, collection_id=video_frames_collection_id, samples=frames_to_create
    )
    annotation_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="label_for_video_frame",
    )

    # Create annotations linked to a video frame sample.
    # First annotation linked to video frame of b_video (file path /path/to/b_video.mp4)
    # Second annotation linked to video frame of a_video (file path /path/to/a_video.mp4)
    # This is to test that retrieval is ordered by sample file path.
    create_annotation(
        session=db_session,
        sample_id=video_frame_ids[0],
        annotation_label_id=annotation_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=video_frame_ids[1],
        annotation_label_id=annotation_label.annotation_label_id,
        collection_id=collection_id,
    )
    retrieved_annotations = annotation_resolver.get_all(session=db_session)
    # Check the order of retrieved annotations is by sample file path
    assert retrieved_annotations.annotations[0].parent_sample_id == video_frame_ids[1]
    assert retrieved_annotations.annotations[1].parent_sample_id == video_frame_ids[0]


def test_get_by_ids(db_session: Session, test_data: _TestData) -> None:
    dog_annotation1 = test_data.dog_annotation1
    cat_annotation = test_data.cat_annotation

    retrieved_annotations = annotation_resolver.get_by_ids(
        session=db_session,
        annotation_ids=[dog_annotation1.sample_id, cat_annotation.sample_id],
    )

    assert len(retrieved_annotations) == 2
    assert dog_annotation1 in retrieved_annotations
    assert cat_annotation in retrieved_annotations


def test_get_all_with_mulpiple_labels(db_session: Session, test_data: _TestData) -> None:
    dog_label = test_data.dog_label
    cat_label = test_data.cat_label

    annotations = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            annotation_label_ids=[
                dog_label.annotation_label_id,
                cat_label.annotation_label_id,
            ]
        ),
    ).annotations
    assert len(annotations) == 3
    assert all(
        a.annotation_label_id in {dog_label.annotation_label_id, cat_label.annotation_label_id}
        for a in annotations
    )


def test_get_all_returns_paginated_results(
    db_session: Session,
    # We need the fixture to create test data.
    test_data: _TestData,  # noqa ARG001
) -> None:
    # Test pagination
    annotations = annotation_resolver.get_all(
        session=db_session, pagination=Paginated(offset=0, limit=3)
    ).annotations
    assert len(annotations) == 3

    # Test pagination with offset
    annotations = annotation_resolver.get_all(
        session=db_session, pagination=Paginated(offset=3, limit=3)
    ).annotations
    assert len(annotations) == 1


def test_get_all_returns_total_count(
    db_session: Session,
    # We need the fixture to create test data.
    test_data: _TestData,  # noqa ARG001
) -> None:
    # Test total count without pagination
    annotations_result = annotation_resolver.get_all(
        session=db_session, pagination=Paginated(offset=0, limit=90)
    )
    assert len(annotations_result.annotations) == 4

    # Test pagination with offset
    annotations_result = annotation_resolver.get_all(
        session=db_session, pagination=Paginated(offset=0, limit=2)
    )
    assert annotations_result.total_count == 4


def test_get_all_returns_filtered_results(db_session: Session, test_data: _TestData) -> None:
    dog_label = test_data.dog_label

    annotations = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            annotation_label_ids=[
                dog_label.annotation_label_id,
            ]
        ),
    ).annotations

    assert len(annotations) == 2


def test_get_all_with_filtered_results_returns_total_count(
    db_session: Session, test_data: _TestData
) -> None:
    dog_label = test_data.dog_label

    annotations = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            annotation_label_ids=[
                dog_label.annotation_label_id,
            ]
        ),
        pagination=Paginated(offset=0, limit=1),
    )

    assert len(annotations.annotations) == 1
    assert annotations.total_count == 2


def test_get_all_returns_filtered_and_paginated_results(
    db_session: Session,
    test_data: _TestData,
) -> None:
    dog_label = test_data.dog_label
    cat_label = test_data.cat_label

    filters = AnnotationsFilter(
        annotation_label_ids=[
            dog_label.annotation_label_id,
            cat_label.annotation_label_id,
        ]
    )
    annotations = annotation_resolver.get_all(
        session=db_session,
        filters=filters,
        pagination=Paginated(
            offset=0,
            limit=2,
        ),
    ).annotations
    assert len(annotations) == 2

    annotations = annotation_resolver.get_all(
        session=db_session,
        filters=filters,
        pagination=Paginated(
            offset=2,
            limit=2,
        ),
    ).annotations
    assert len(annotations) == 1


def test_get_all_returns_filtered_by_collection_results(
    db_session: Session,
    test_data: _TestData,
) -> None:
    collection = test_data.collection
    collection2 = test_data.collection2

    annotations_for_collection1 = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            collection_ids=[
                collection.children[0].collection_id,
            ]
        ),
    ).annotations
    assert len(annotations_for_collection1) == 3

    annotations_for_collection2 = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            collection_ids=[
                collection2.children[0].collection_id,
            ]
        ),
    ).annotations
    assert len(annotations_for_collection2) == 1

    annotations_for_both_collections = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            collection_ids=[
                collection.children[0].collection_id,
                collection2.children[0].collection_id,
            ]
        ),
    ).annotations
    assert len(annotations_for_both_collections) == 4


def test_get_all_by_collection_name(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )

    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=image.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                x=10,
                y=10,
                width=50,
                height=50,
            )
        ],
        collection_name="ground_truth",
    )

    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=[
            AnnotationCreate(
                parent_sample_id=image.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
                x=12,
                y=13,
                width=47,
                height=52,
                confidence=0.7,
            )
        ],
        collection_name="predictions",
    )

    ground_truth = annotation_resolver.get_all_by_collection_name(
        session=db_session,
        collection_name="ground_truth",
        parent_collection_id=collection.collection_id,
    ).annotations
    assert len(ground_truth) == 1
    assert ground_truth[0].object_detection_details is not None
    assert ground_truth[0].object_detection_details.x == 10
    assert ground_truth[0].object_detection_details.y == 10
    assert ground_truth[0].object_detection_details.width == 50
    assert ground_truth[0].object_detection_details.height == 50

    prediction = annotation_resolver.get_all_by_collection_name(
        session=db_session,
        collection_name="predictions",
        parent_collection_id=collection.collection_id,
    ).annotations
    assert len(prediction) == 1
    assert prediction[0].object_detection_details is not None
    assert prediction[0].object_detection_details.x == 12
    assert prediction[0].object_detection_details.y == 13
    assert prediction[0].object_detection_details.width == 47
    assert prediction[0].object_detection_details.height == 52
    assert prediction[0].confidence == pytest.approx(0.7)

    # Test with non-existent collection name
    with pytest.raises(ValueError, match=r"Collection with name 'non-existent' does not exist."):
        annotation_resolver.get_all_by_collection_name(
            session=db_session,
            collection_name="non-existent",
            parent_collection_id=collection.collection_id,
        )


def test_get_all_ordered_by_sample_file_path(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    image_2 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/z_dir/sample_2.png"
    )
    image_1 = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/a_dir/sample_1.png"
    )

    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="test"
    )

    sample_2_ann_1 = create_annotation(
        session=db_session,
        sample_id=image_2.sample_id,
        annotation_label_id=label.annotation_label_id,
        collection_id=collection_id,
    )
    sample_1_ann_1 = create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=label.annotation_label_id,
        collection_id=collection_id,
    )
    sample_1_ann_2 = create_annotation(
        session=db_session,
        sample_id=image_1.sample_id,
        annotation_label_id=label.annotation_label_id,
        collection_id=collection_id,
    )

    ordered_annotations = annotation_resolver.get_all(session=db_session).annotations
    assert len(ordered_annotations) == 3
    assert ordered_annotations == [
        sample_1_ann_1,
        sample_1_ann_2,
        sample_2_ann_1,
    ]


def test_get_all__with_tag_filtering(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    tag_1 = create_tag(
        session=db_session,
        collection_id=collection.collection_id,
        tag_name="tag_all",
        kind="annotation",
    )
    tag_2 = create_tag(
        session=db_session,
        collection_id=collection.collection_id,
        tag_name="tag_odd",
        kind="annotation",
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    anno_label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    anno_label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )

    total_annos = 10
    annotations = []
    for i in range(total_annos):
        annotation = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=anno_label_cat.annotation_label_id
            if i < total_annos / 2
            else anno_label_dog.annotation_label_id,
        )
        annotations.append(annotation)

    # add first half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_1.tag_id,
        sample_ids=[
            annotation.sample_id
            for _, annotation in enumerate(annotations)
            if annotation.annotation_label_id == anno_label_cat.annotation_label_id
        ],
    )

    # add second half to tag_1
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_2.tag_id,
        sample_ids=[
            annotation.sample_id
            for _, annotation in enumerate(annotations)
            if annotation.annotation_label_id == anno_label_dog.annotation_label_id
        ],
    )

    # Test filtering by tags
    annotations_part1 = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            collection_ids=[collection.children[0].collection_id],
            tag_ids=[tag_1.tag_id],
        ),
    ).annotations
    assert len(annotations_part1) == int(total_annos / 2)
    assert all(
        annotation.annotation_label.annotation_label_name == "cat"
        for annotation in annotations_part1
    )

    annotations_part2 = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            collection_ids=[collection.children[0].collection_id],
            tag_ids=[tag_2.tag_id],
        ),
    ).annotations
    assert len(annotations_part2) == int(total_annos / 2)
    assert all(
        annotation.annotation_label.annotation_label_name == "dog"
        for annotation in annotations_part2
    )

    # test filtering by both tags
    annotations_all = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(
            collection_ids=[collection.children[0].collection_id],
            tag_ids=[tag_1.tag_id, tag_2.tag_id],
        ),
    ).annotations
    assert len(annotations_all) == total_annos


def test_create_many_annotations(db_session: Session) -> None:
    """Test bulk creation of annotations."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    cat_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )

    annotations_to_create = [
        AnnotationCreate(
            parent_sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            x=i * 10,
            y=i * 10,
            width=50,
            height=50,
        )
        for i in range(3)
    ]

    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=annotations_to_create,
    )

    created_annotations = annotation_resolver.get_all(
        session=db_session,
        filters=AnnotationsFilter(collection_ids=[collection.children[0].collection_id]),
    ).annotations

    assert len(created_annotations) == 3
    assert all(
        anno.sample.collection_id == collection.children[0].collection_id
        for anno in created_annotations
    )
    assert all(anno.parent_sample_id == image.sample_id for anno in created_annotations)
    assert all(
        anno.annotation_label_id == cat_label.annotation_label_id for anno in created_annotations
    )


def test_create_many__populates_coverage(db_session: Session) -> None:
    """Creating annotations must also populate the AnnotationCollectionCoverageTable."""
    collection = create_collection(session=db_session)
    label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    images = [
        create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs=f"/img_{i}.png",
        )
        for i in range(2)
    ]

    # Create annotations for images[0] and images[1].
    annotations_to_create = [
        AnnotationCreate(
            parent_sample_id=img.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            x=0,
            y=0,
            width=10,
            height=10,
        )
        for img in images
    ]
    annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collection.collection_id,
        annotations=annotations_to_create,
    )

    annotation_collection_id = collection.children[0].collection_id
    covered = annotation_collection_coverage_resolver.list_by_collection_id(
        session=db_session, annotation_collection_id=annotation_collection_id
    )
    assert set(covered) == {images[0].sample_id, images[1].sample_id}
