from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.dataset import DatasetTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameCreate
from lightly_studio.resolvers import (
    annotation_resolver,
    dataset_resolver,
    tag_resolver,
    video_frame_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_dataset,
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
    dataset: DatasetTable
    sample1: ImageTable
    sample2: ImageTable
    mouse_annotation: AnnotationBaseTable
    dataset2: DatasetTable
    sample_with_mouse: ImageTable


@pytest.fixture
def test_data(test_db: Session) -> _TestData:
    """Fixture that provides test database with sample data."""
    dataset1 = create_dataset(session=test_db)
    dataset1_id = dataset1.dataset_id

    dataset2 = create_dataset(session=test_db, dataset_name="dataset2")
    dataset2_id = dataset2.dataset_id

    # Create samples
    image1 = create_image(
        session=test_db, dataset_id=dataset1_id, file_path_abs="/path/to/sample1.png"
    )
    image2 = create_image(
        session=test_db, dataset_id=dataset1_id, file_path_abs="/path/to/sample2.png"
    )

    image_with_mouse = create_image(
        session=test_db, dataset_id=dataset2_id, file_path_abs="/path/to/sample_with_mouse.png"
    )

    # Create labels
    dog_label = create_annotation_label(
        session=test_db,
        annotation_label_name="dog",
    )
    cat_label = create_annotation_label(
        session=test_db,
        annotation_label_name="cat",
    )
    mouse_label = create_annotation_label(
        session=test_db,
        annotation_label_name="mouse",
    )

    # Create annotations
    dog_annotation1 = create_annotation(
        session=test_db,
        sample_id=image1.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        dataset_id=dataset1_id,
    )
    dog_annotation2 = create_annotation(
        session=test_db,
        sample_id=image2.sample_id,
        annotation_label_id=dog_label.annotation_label_id,
        dataset_id=dataset1_id,
        annotation_data={
            "segmentation__binary_mask__rle_row_wise": [1, 2, 3],
        },
    )
    cat_annotation = create_annotation(
        session=test_db,
        sample_id=image1.sample_id,
        annotation_label_id=cat_label.annotation_label_id,
        dataset_id=dataset1_id,
    )
    mouse_annotation = create_annotation(
        session=test_db,
        sample_id=image_with_mouse.sample_id,
        annotation_label_id=mouse_label.annotation_label_id,
        dataset_id=dataset2_id,
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
        dataset=dataset1,
        sample1=image1,
        sample2=image2,
        mouse_annotation=mouse_annotation,
        dataset2=dataset2,
        sample_with_mouse=image_with_mouse,
    )


def test_create_and_get_annotation(test_db: Session, test_data: _TestData) -> None:
    dog_annotation = test_data.dog_annotation1

    retrieved_annotation = annotation_resolver.get_by_id(
        session=test_db, annotation_id=dog_annotation.sample_id
    )

    assert retrieved_annotation == dog_annotation


def test_create_and_get_annotation__for_video_frame_with_ordering(test_db: Session) -> None:
    dataset_id = create_dataset(session=test_db, sample_type=SampleType.VIDEO).dataset_id

    # Create video.
    video_ids = create_videos(
        session=test_db,
        dataset_id=dataset_id,
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

    video_frames_dataset_id = dataset_resolver.get_or_create_child_dataset(
        session=test_db, dataset_id=dataset_id, sample_type=SampleType.VIDEO_FRAME
    )
    video_frame_ids = video_frame_resolver.create_many(
        session=test_db, dataset_id=video_frames_dataset_id, samples=frames_to_create
    )
    annotation_label = create_annotation_label(
        session=test_db,
        annotation_label_name="label_for_video_frame",
    )

    # Create annotations linked to a video frame sample.
    # First annotation linked to video frame of b_video (file path /path/to/b_video.mp4)
    # Second annotation linked to video frame of a_video (file path /path/to/a_video.mp4)
    # This is to test that retrieval is ordered by sample file path.
    create_annotation(
        session=test_db,
        sample_id=video_frame_ids[0],
        annotation_label_id=annotation_label.annotation_label_id,
        dataset_id=dataset_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_ids[1],
        annotation_label_id=annotation_label.annotation_label_id,
        dataset_id=dataset_id,
    )
    retrieved_annotations = annotation_resolver.get_all(session=test_db)
    # Check the order of retrieved annotations is by sample file path
    assert retrieved_annotations.annotations[0].parent_sample_id == video_frame_ids[1]
    assert retrieved_annotations.annotations[1].parent_sample_id == video_frame_ids[0]


def test_count_annotations_labels_by_dataset(test_db: Session, test_data: _TestData) -> None:
    dataset = test_data.dataset

    annotation_counts = annotation_resolver.count_annotations_by_dataset(
        session=test_db, dataset_id=dataset.dataset_id
    )

    assert len(annotation_counts) == 2
    annotation_dict = {label: current for (label, current, _) in annotation_counts}
    assert annotation_dict["dog"] == 2
    assert annotation_dict["cat"] == 1


def test_count_annotations_by_dataset_with_filtering(
    test_db: Session,
    test_data: _TestData,
) -> None:
    dataset = test_data.dataset
    dataset_id = dataset.dataset_id

    # Test without filtering
    counts = annotation_resolver.count_annotations_by_dataset(
        session=test_db, dataset_id=dataset_id
    )
    counts_dict = {label: (current, total) for label, current, total in counts}
    assert counts_dict["dog"] == (
        2,
        2,
    )  # current_count = total_count when no filtering
    assert counts_dict["cat"] == (1, 1)

    # Test with filtering by "dog"
    filtered_counts = annotation_resolver.count_annotations_by_dataset(
        session=test_db, dataset_id=dataset_id, filtered_labels=["dog"]
    )
    filtered_dict = {label: (current, total) for label, current, total in filtered_counts}
    assert filtered_dict["dog"] == (2, 2)  # All dogs are visible
    assert filtered_dict["cat"] == (
        1,
        1,
    )  # Cat from sample1 is visible (because sample1 has a dog)

    # Test with filtering by "cat"
    filtered_counts = annotation_resolver.count_annotations_by_dataset(
        session=test_db, dataset_id=dataset_id, filtered_labels=["cat"]
    )
    filtered_dict = {label: (current, total) for label, current, total in filtered_counts}
    assert filtered_dict["dog"] == (
        1,
        2,
    )  # Only one dog is visible (from sample1)
    assert filtered_dict["cat"] == (1, 1)  # All cats are visible


def test_get_by_ids(test_db: Session, test_data: _TestData) -> None:
    dog_annotation1 = test_data.dog_annotation1
    cat_annotation = test_data.cat_annotation

    retrieved_annotations = annotation_resolver.get_by_ids(
        session=test_db,
        annotation_ids=[dog_annotation1.sample_id, cat_annotation.sample_id],
    )

    assert len(retrieved_annotations) == 2
    assert dog_annotation1 in retrieved_annotations
    assert cat_annotation in retrieved_annotations


def test_get_all_with_mulpiple_labels(test_db: Session, test_data: _TestData) -> None:
    dog_label = test_data.dog_label
    cat_label = test_data.cat_label

    annotations = annotation_resolver.get_all(
        session=test_db,
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
    test_db: Session,
    # We need the fixture to create test data.
    test_data: _TestData,  # noqa ARG001
) -> None:
    # Test pagination
    annotations = annotation_resolver.get_all(
        session=test_db, pagination=Paginated(offset=0, limit=3)
    ).annotations
    assert len(annotations) == 3

    # Test pagination with offset
    annotations = annotation_resolver.get_all(
        session=test_db, pagination=Paginated(offset=3, limit=3)
    ).annotations
    assert len(annotations) == 1


def test_get_all_returns_total_count(
    test_db: Session,
    # We need the fixture to create test data.
    test_data: _TestData,  # noqa ARG001
) -> None:
    # Test total count without pagination
    annotations_result = annotation_resolver.get_all(
        session=test_db, pagination=Paginated(offset=0, limit=90)
    )
    assert len(annotations_result.annotations) == 4

    # Test pagination with offset
    annotations_result = annotation_resolver.get_all(
        session=test_db, pagination=Paginated(offset=0, limit=2)
    )
    assert annotations_result.total_count == 4


def test_get_all_returns_filtered_results(test_db: Session, test_data: _TestData) -> None:
    dog_label = test_data.dog_label

    annotations = annotation_resolver.get_all(
        session=test_db,
        filters=AnnotationsFilter(
            annotation_label_ids=[
                dog_label.annotation_label_id,
            ]
        ),
    ).annotations

    assert len(annotations) == 2


def test_get_all_with_filtered_results_returns_total_count(
    test_db: Session, test_data: _TestData
) -> None:
    dog_label = test_data.dog_label

    annotations = annotation_resolver.get_all(
        session=test_db,
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
    test_db: Session,
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
        session=test_db,
        filters=filters,
        pagination=Paginated(
            offset=0,
            limit=2,
        ),
    ).annotations
    assert len(annotations) == 2

    annotations = annotation_resolver.get_all(
        session=test_db,
        filters=filters,
        pagination=Paginated(
            offset=2,
            limit=2,
        ),
    ).annotations
    assert len(annotations) == 1


def test_get_all_returns_filtered_by_dataset_results(
    test_db: Session,
    test_data: _TestData,
) -> None:
    dataset = test_data.dataset
    dataset2 = test_data.dataset2

    annotations_for_dataset1 = annotation_resolver.get_all(
        session=test_db,
        filters=AnnotationsFilter(
            dataset_ids=[
                dataset.children[0].dataset_id,
            ]
        ),
    ).annotations
    assert len(annotations_for_dataset1) == 3

    annotations_for_dataset2 = annotation_resolver.get_all(
        session=test_db,
        filters=AnnotationsFilter(
            dataset_ids=[
                dataset2.children[0].dataset_id,
            ]
        ),
    ).annotations
    assert len(annotations_for_dataset2) == 1

    annotations_for_both_datasets = annotation_resolver.get_all(
        session=test_db,
        filters=AnnotationsFilter(
            dataset_ids=[
                dataset.children[0].dataset_id,
                dataset2.children[0].dataset_id,
            ]
        ),
    ).annotations
    assert len(annotations_for_both_datasets) == 4


def test_get_all_ordered_by_sample_file_path(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id

    image_2 = create_image(
        session=test_db, dataset_id=dataset_id, file_path_abs="/z_dir/sample_2.png"
    )
    image_1 = create_image(
        session=test_db, dataset_id=dataset_id, file_path_abs="/a_dir/sample_1.png"
    )

    label = create_annotation_label(session=test_db, annotation_label_name="test")

    sample_2_ann_1 = create_annotation(
        session=test_db,
        sample_id=image_2.sample_id,
        annotation_label_id=label.annotation_label_id,
        dataset_id=dataset_id,
    )
    sample_1_ann_1 = create_annotation(
        session=test_db,
        sample_id=image_1.sample_id,
        annotation_label_id=label.annotation_label_id,
        dataset_id=dataset_id,
    )
    sample_1_ann_2 = create_annotation(
        session=test_db,
        sample_id=image_1.sample_id,
        annotation_label_id=label.annotation_label_id,
        dataset_id=dataset_id,
    )

    ordered_annotations = annotation_resolver.get_all(session=test_db).annotations
    assert len(ordered_annotations) == 3
    assert ordered_annotations == [
        sample_1_ann_1,
        sample_1_ann_2,
        sample_2_ann_1,
    ]


def test_add_tag_to_annotation(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    tag = create_tag(session=test_db, dataset_id=dataset.dataset_id, kind="annotation")
    image = create_image(session=test_db, dataset_id=dataset.dataset_id)
    anno_label_cat = create_annotation_label(session=test_db, annotation_label_name="cat")
    annotation = create_annotation(
        session=test_db,
        dataset_id=dataset.dataset_id,
        sample_id=image.sample_id,
        annotation_label_id=anno_label_cat.annotation_label_id,
    )

    # add annotaiton to tag
    tag_resolver.add_tag_to_annotation(session=test_db, tag_id=tag.tag_id, annotation=annotation)

    assert annotation.tags.index(tag) == 0


def test_add_tag_to_annotation__ensure_correct_kind(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag_with_wrong_kind = create_tag(session=test_db, dataset_id=dataset_id, kind="sample")
    image = create_image(session=test_db, dataset_id=dataset.dataset_id)
    anno_label_cat = create_annotation_label(session=test_db, annotation_label_name="cat")
    annotation = create_annotation(
        session=test_db,
        dataset_id=dataset.dataset_id,
        sample_id=image.sample_id,
        annotation_label_id=anno_label_cat.annotation_label_id,
    )

    # adding sample to tag with wrong kind raises ValueError
    with pytest.raises(ValueError, match="is not of kind 'annotation'"):
        tag_resolver.add_tag_to_annotation(
            session=test_db,
            tag_id=tag_with_wrong_kind.tag_id,
            annotation=annotation,
        )


def test_remove_annotation_from_tag(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    tag = create_tag(session=test_db, dataset_id=dataset.dataset_id, kind="annotation")
    image = create_image(session=test_db, dataset_id=dataset.dataset_id)
    anno_label_cat = create_annotation_label(session=test_db, annotation_label_name="cat")
    annotation = create_annotation(
        session=test_db,
        dataset_id=dataset.dataset_id,
        sample_id=image.sample_id,
        annotation_label_id=anno_label_cat.annotation_label_id,
    )

    # add annotation to tag
    tag_resolver.add_tag_to_annotation(session=test_db, tag_id=tag.tag_id, annotation=annotation)
    assert len(annotation.tags) == 1
    assert annotation.tags.index(tag) == 0

    # remove annotation to tag
    tag_resolver.remove_tag_from_annotation(
        session=test_db, tag_id=tag.tag_id, annotation=annotation
    )
    assert len(annotation.tags) == 0
    with pytest.raises(ValueError, match="is not in list"):
        annotation.tags.index(tag)


def test_add_and_remove_annotation_ids_to_tag_id(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    tag_1 = create_tag(
        session=test_db,
        dataset_id=dataset.dataset_id,
        tag_name="tag_all",
        kind="annotation",
    )
    tag_2 = create_tag(
        session=test_db,
        dataset_id=dataset.dataset_id,
        tag_name="tag_odd",
        kind="annotation",
    )
    image = create_image(session=test_db, dataset_id=dataset.dataset_id)
    anno_label_cat = create_annotation_label(session=test_db, annotation_label_name="cat")

    total_annos = 10
    annotations = []
    for _ in range(total_annos):
        annotation = create_annotation(
            session=test_db,
            dataset_id=dataset.dataset_id,
            sample_id=image.sample_id,
            annotation_label_id=anno_label_cat.annotation_label_id,
        )
        annotations.append(annotation)

    # add all annotations to tag_1
    tag_resolver.add_annotation_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        annotation_ids=[annotation.sample_id for annotation in annotations],
    )

    # add every odd annotations to tag_2
    tag_resolver.add_annotation_ids_to_tag_id(
        session=test_db,
        tag_id=tag_2.tag_id,
        annotation_ids=[
            annotation.sample_id for i, annotation in enumerate(annotations) if i % 2 == 1
        ],
    )

    # ensure all annotations were added to the correct tags
    for i, annotation in enumerate(annotations):
        assert tag_1 in annotation.tags
        if i % 2 == 1:
            assert tag_2 in annotation.tags

    # ensure the correct number of annotations were added to each tag
    assert len(tag_1.annotations) == total_annos
    assert len(tag_2.annotations) == total_annos / 2

    # lets remove every even annotations from tag_1
    # this results in tag_1 and tag_2 having the same annotations
    annotation_ids_to_remove = [
        annotation.sample_id for i, annotation in enumerate(annotations) if i % 2 == 0
    ]
    tag_resolver.remove_annotation_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        annotation_ids=annotation_ids_to_remove,
    )

    assert len(tag_1.annotations) == total_annos / 2
    assert len(tag_2.annotations) == total_annos / 2
    assert {a.sample_id for a in tag_1.annotations} == {a.sample_id for a in tag_2.annotations}


def test_add_and_remove_annotation_ids_to_tag_id__twice_same_annotation_ids(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag_1 = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_all",
        kind="annotation",
    )
    image = create_image(session=test_db, dataset_id=dataset.dataset_id)
    anno_label_cat = create_annotation_label(session=test_db, annotation_label_name="cat")

    total_annos = 10
    annotations = []
    for _ in range(total_annos):
        annotation = create_annotation(
            session=test_db,
            dataset_id=dataset.dataset_id,
            sample_id=image.sample_id,
            annotation_label_id=anno_label_cat.annotation_label_id,
        )
        annotations.append(annotation)

    # add annotations to tag_1
    tag_resolver.add_annotation_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        annotation_ids=[annotation.sample_id for annotation in annotations],
    )

    # adding the same annotations to tag_1 does not create an error
    tag_resolver.add_annotation_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        annotation_ids=[annotation.sample_id for annotation in annotations],
    )

    # ensure all annotations were added once
    assert len(tag_1.annotations) == total_annos

    # remove sampels from
    tag_resolver.remove_annotation_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        annotation_ids=[annotation.sample_id for annotation in annotations],
    )
    # removing the same annotations to tag_1 does not create an error
    tag_resolver.remove_annotation_ids_from_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        annotation_ids=[annotation.sample_id for annotation in annotations],
    )

    # ensure all annotations were removed again
    assert len(tag_1.annotations) == 0


def test_add_and_remove_annotation_ids_to_tag_id__ensure_correct_kind(
    test_db: Session,
) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.dataset_id
    tag_with_wrong_kind = create_tag(
        session=test_db,
        dataset_id=dataset_id,
        tag_name="tag_with_wrong_kind",
        kind="sample",
    )

    image = create_image(session=test_db, dataset_id=dataset.dataset_id)
    anno_label_cat = create_annotation_label(session=test_db, annotation_label_name="cat")
    annotation = create_annotation(
        session=test_db,
        dataset_id=dataset.dataset_id,
        sample_id=image.sample_id,
        annotation_label_id=anno_label_cat.annotation_label_id,
    )

    # adding annotations to tag with wrong kind raises ValueError
    with pytest.raises(ValueError, match="is not of kind 'annotation'"):
        tag_resolver.add_annotation_ids_to_tag_id(
            session=test_db,
            tag_id=tag_with_wrong_kind.tag_id,
            annotation_ids=[annotation.sample_id],
        )


def test_get_all__with_tag_filtering(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    tag_1 = create_tag(
        session=test_db,
        dataset_id=dataset.dataset_id,
        tag_name="tag_all",
        kind="annotation",
    )
    tag_2 = create_tag(
        session=test_db,
        dataset_id=dataset.dataset_id,
        tag_name="tag_odd",
        kind="annotation",
    )
    image = create_image(session=test_db, dataset_id=dataset.dataset_id)
    anno_label_cat = create_annotation_label(session=test_db, annotation_label_name="cat")
    anno_label_dog = create_annotation_label(session=test_db, annotation_label_name="dog")

    total_annos = 10
    annotations = []
    for i in range(total_annos):
        annotation = create_annotation(
            session=test_db,
            dataset_id=dataset.dataset_id,
            sample_id=image.sample_id,
            annotation_label_id=anno_label_cat.annotation_label_id
            if i < total_annos / 2
            else anno_label_dog.annotation_label_id,
        )
        annotations.append(annotation)

    # add first half to tag_1
    tag_resolver.add_annotation_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1.tag_id,
        annotation_ids=[
            annotation.sample_id
            for _, annotation in enumerate(annotations)
            if annotation.annotation_label_id == anno_label_cat.annotation_label_id
        ],
    )

    # add second half to tag_1
    tag_resolver.add_annotation_ids_to_tag_id(
        session=test_db,
        tag_id=tag_2.tag_id,
        annotation_ids=[
            annotation.sample_id
            for _, annotation in enumerate(annotations)
            if annotation.annotation_label_id == anno_label_dog.annotation_label_id
        ],
    )

    # Test filtering by tags
    annotations_part1 = annotation_resolver.get_all(
        session=test_db,
        filters=AnnotationsFilter(
            dataset_ids=[dataset.children[0].dataset_id],
            annotation_tag_ids=[tag_1.tag_id],
        ),
    ).annotations
    assert len(annotations_part1) == int(total_annos / 2)
    assert all(
        annotation.annotation_label.annotation_label_name == "cat"
        for annotation in annotations_part1
    )

    annotations_part2 = annotation_resolver.get_all(
        session=test_db,
        filters=AnnotationsFilter(
            dataset_ids=[dataset.children[0].dataset_id],
            annotation_tag_ids=[tag_2.tag_id],
        ),
    ).annotations
    assert len(annotations_part2) == int(total_annos / 2)
    assert all(
        annotation.annotation_label.annotation_label_name == "dog"
        for annotation in annotations_part2
    )

    # test filtering by both tags
    annotations_all = annotation_resolver.get_all(
        session=test_db,
        filters=AnnotationsFilter(
            dataset_ids=[dataset.children[0].dataset_id],
            annotation_tag_ids=[tag_1.tag_id, tag_2.tag_id],
        ),
    ).annotations
    assert len(annotations_all) == total_annos


def test_create_many_annotations(test_db: Session) -> None:
    """Test bulk creation of annotations."""
    dataset = create_dataset(session=test_db)
    image = create_image(session=test_db, dataset_id=dataset.dataset_id)
    cat_label = create_annotation_label(session=test_db, annotation_label_name="cat")

    annotations_to_create = [
        AnnotationCreate(
            parent_sample_id=image.sample_id,
            annotation_label_id=cat_label.annotation_label_id,
            annotation_type="object_detection",
            x=i * 10,
            y=i * 10,
            width=50,
            height=50,
        )
        for i in range(3)
    ]

    annotation_resolver.create_many(
        session=test_db, parent_dataset_id=dataset.dataset_id, annotations=annotations_to_create
    )

    created_annotations = annotation_resolver.get_all(
        session=test_db,
        filters=AnnotationsFilter(dataset_ids=[dataset.children[0].dataset_id]),
    ).annotations

    assert len(created_annotations) == 3
    assert all(anno.dataset_id == dataset.children[0].dataset_id for anno in created_annotations)
    assert all(anno.parent_sample_id == image.sample_id for anno in created_annotations)
    assert all(
        anno.annotation_label_id == cat_label.annotation_label_id for anno in created_annotations
    )
