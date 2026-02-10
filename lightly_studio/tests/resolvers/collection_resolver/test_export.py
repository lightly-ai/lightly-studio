from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import collection_resolver, tag_resolver
from lightly_studio.resolvers.collection_resolver.export import ExportFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)


@dataclass
class TestcollectionExport:
    collection: CollectionTable
    samples: list[ImageTable]
    annotations: list[AnnotationBaseTable]
    tags: dict[str, TagTable]
    samples_total: int
    annotations_total: int


@pytest.fixture
def test_collection_export(test_db: Session) -> TestcollectionExport:
    samples_total = 20
    annotations_per_sample = 2
    annotations_total = samples_total * annotations_per_sample

    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    # create annotation_tag
    cat_label = create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="cat",
    )
    dog_label = create_annotation_label(
        session=test_db,
        dataset_id=collection_id,
        label_name="dog",
    )

    # create samples and an annotation per sample
    images = []
    annotations = []
    for i in range(samples_total):
        image = create_image(
            session=test_db,
            collection_id=collection_id,
            file_path_abs=f"/path/to/sample{i}.png",
        )
        images.append(image)

        # add annotations per sample
        for a in range(annotations_per_sample):
            annotations.append(
                create_annotation(
                    session=test_db,
                    collection_id=collection_id,
                    sample_id=image.sample_id,
                    annotation_label_id=cat_label.annotation_label_id
                    if a % 2 == 0
                    else dog_label.annotation_label_id,
                )
            )

    # create sample tags
    tag_1_of_4 = create_tag(
        session=test_db,
        collection_id=collection_id,
        tag_name="tag 1/4",
        kind="sample",
    )
    tag_4_of_4 = create_tag(
        session=test_db,
        collection_id=collection_id,
        tag_name="tag 4/4",
        kind="sample",
    )
    tag_mod_2 = create_tag(
        session=test_db,
        collection_id=collection_id,
        tag_name="tag mmod2",
        kind="sample",
    )

    # create tags for annotations
    anno_tag_1_of_4 = create_tag(
        session=test_db,
        collection_id=collection_id,
        tag_name="anno tag 1/4",
        kind="annotation",
    )
    anno_tag_4_of_4 = create_tag(
        session=test_db,
        collection_id=collection_id,
        tag_name="anno tag 4/4",
        kind="annotation",
    )
    anno_tag_mod_2 = create_tag(
        session=test_db,
        collection_id=collection_id,
        tag_name="anno tag mmod2",
        kind="annotation",
    )

    # add samples to tags
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_1_of_4.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i < samples_total / 4],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_4_of_4.tag_id,
        sample_ids=[
            sample.sample_id for i, sample in enumerate(images) if i >= samples_total / 4 * 3
        ],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag_mod_2.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i % 2 == 0],
    )

    # add annotations to tags
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=anno_tag_1_of_4.tag_id,
        sample_ids=[
            annotation.sample_id
            for i, annotation in enumerate(annotations)
            if i < annotations_total / 4
        ],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=anno_tag_4_of_4.tag_id,
        sample_ids=[
            annotation.sample_id
            for i, annotation in enumerate(annotations)
            if i >= annotations_total / 4 * 3
        ],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=anno_tag_mod_2.tag_id,
        sample_ids=[annotation.sample_id for i, annotation in enumerate(annotations) if i % 2 == 0],
    )

    # add second collection to ensure we properly scope it to one collection
    collection2 = create_collection(session=test_db, collection_name="collection2")
    image2 = create_image(
        session=test_db,
        collection_id=collection2.collection_id,
        file_path_abs="/second/collection/sample.png",
    )
    parrot_label = create_annotation_label(
        session=test_db,
        dataset_id=collection2.collection_id,
        label_name="parrot",
    )
    create_annotation(
        session=test_db,
        collection_id=collection2.collection_id,
        sample_id=image2.sample_id,
        annotation_label_id=parrot_label.annotation_label_id,
    )

    return TestcollectionExport(
        collection=collection,
        samples=images,
        annotations=annotations,
        tags={
            # sample tags
            "tag_1_of_4": tag_1_of_4,
            "tag_4_of_4": tag_4_of_4,
            "tag_mod_2": tag_mod_2,
            # annotation tags
            "anno_tag_1_of_4": anno_tag_1_of_4,
            "anno_tag_4_of_4": anno_tag_4_of_4,
            "anno_tag_mod_2": anno_tag_mod_2,
        },
        samples_total=samples_total,
        annotations_total=annotations_total,
    )


def test_export__include_or_exclude__both_provided(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]

    with pytest.raises(ValueError, match="Cannot include and exclude at the same time."):
        collection_resolver.export(
            session=test_db,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
            exclude=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
        )


def test_export__include_or_exclude__none_provided(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    with pytest.raises(ValueError, match="Include or exclude filter is required."):
        collection_resolver.export(
            session=test_db, collection_id=test_collection_export.collection.collection_id
        )


def test_export__include_no_empty_list_provided(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    with pytest.raises(ValueError, match="List should have at least 1 item"):
        collection_resolver.export(
            session=test_db,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(tag_ids=[]),
        )
    with pytest.raises(ValueError, match="List should have at least 1 item"):
        collection_resolver.export(
            session=test_db,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(sample_ids=[]),
        )
    with pytest.raises(ValueError, match="List should have at least 1 item"):
        collection_resolver.export(
            session=test_db,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(annotation_ids=[]),
        )


def test_export__include_with_either_tag_ids_or_sample_ids_or_annotation_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    sample = test_collection_export.samples[0]
    annotation = test_collection_export.annotations[0]

    with pytest.raises(
        ValueError,
        match="Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        collection_resolver.export(
            session=test_db,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(tag_ids=[tag_1_of_4.tag_id], sample_ids=[sample.sample_id]),
        )

    with pytest.raises(
        ValueError,
        match="Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        collection_resolver.export(
            session=test_db,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(
                sample_ids=[sample.sample_id],
                annotation_ids=[annotation.sample_id],
            ),
        )

    with pytest.raises(
        ValueError,
        match="Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        collection_resolver.export(
            session=test_db,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(
                annotation_ids=[annotation.sample_id],
                tag_ids=[tag_1_of_4.tag_id],
            ),
        )

    with pytest.raises(
        ValueError,
        match="Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        collection_resolver.export(
            session=test_db,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(
                tag_ids=[tag_1_of_4.tag_id],
                sample_ids=[sample.sample_id],
                annotation_ids=[annotation.sample_id],
            ),
        )


# test export include tags
def test_export__include_single_sample_tag(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]

    # export single tag
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4)


def test_export__include_multiple_sample_tags(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]

    # export multiple tags
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[tag_1_of_4.tag_id, tag_4_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 2)


def test_export__include_multiple_sample_tags__overlapping(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]
    tag_mod_2 = test_collection_export.tags["tag_mod_2"]

    # export multiple tags overlapping
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(
            tag_ids=[
                tag_1_of_4.tag_id,
                tag_4_of_4.tag_id,
                tag_mod_2.tag_id,
            ]
        ),
    )
    assert len(samples_exported) == len(
        {s.sample_id for s in (tag_1_of_4.samples + tag_4_of_4.samples + tag_mod_2.samples)}
    )


# test export include tags
def test_export__include_single_annotation_tag(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]

    # export single tag
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[anno_tag_1_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4)


def test_export__include_multiple_annotation_tags(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]
    anno_tag_4_of_4 = test_collection_export.tags["anno_tag_4_of_4"]

    # export multiple tags
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[anno_tag_1_of_4.tag_id, anno_tag_4_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 2)


def test_export__include_multiple_annotation_tags__overlapping(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]
    anno_tag_4_of_4 = test_collection_export.tags["anno_tag_4_of_4"]
    anno_tag_mod_2 = test_collection_export.tags["anno_tag_mod_2"]

    # export multiple tags overlapping
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(
            tag_ids=[
                anno_tag_1_of_4.tag_id,
                anno_tag_4_of_4.tag_id,
                anno_tag_mod_2.tag_id,
            ]
        ),
    )
    assert len(samples_exported) == int(samples_total)


# test export include sample_ids
def test_export__include_sample_id(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    sample = test_collection_export.samples[-1]

    # export single sample_id
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(sample_ids=[sample.sample_id]),
    )
    assert len(samples_exported) == 1


def test_export__include_multiple_sample_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples = test_collection_export.samples

    # export single tag
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(sample_ids=[sample.sample_id for sample in samples]),
    )
    assert len(samples_exported) == len(samples)


# test export include annotation_ids
def test_export__include_annotation_id(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotation = test_collection_export.annotations[-1]
    sample = test_collection_export.samples[-1]

    # export sample via single annotation_id
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(annotation_ids=[annotation.sample_id]),
    )
    assert len(samples_exported) == 1
    assert samples_exported[0] == sample.file_path_abs
    assert annotation in sample.sample.annotations


def test_export__include_multiple_annotation_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotations = test_collection_export.annotations
    samples = test_collection_export.samples

    # export sample via multiple annotations preventing duplicates
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(
            annotation_ids=[
                # sample 0
                annotations[0].sample_id,
                annotations[1].sample_id,
                # sample 1
                annotations[2].sample_id,
            ]
        ),
    )
    assert len(samples_exported) == 2
    assert samples[0].file_path_abs in samples_exported
    assert samples[1].file_path_abs in samples_exported
    # ensure the annotations belong to the samples
    assert annotations[0] in samples[0].sample.annotations
    assert annotations[1] in samples[0].sample.annotations
    assert annotations[2] in samples[1].sample.annotations


# test export exclude tags
def test_export__exclude_with_either_tag_ids_or_sample_ids(
    test_collection_export: TestcollectionExport,
) -> None:
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    sample = test_collection_export.samples[0]

    with pytest.raises(
        ValueError,
        match="Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        ExportFilter(tag_ids=[tag_1_of_4.tag_id], sample_ids=[sample.sample_id])


def test_export__exclude_single_sample_tag(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]

    # export single tag
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 3)


def test_export__exclude_by_multiple_sample_tags(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]

    # export multiple tags
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[tag_1_of_4.tag_id, tag_4_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 2)


def test_export__exclude_by_multiple_sample_tags__overlapping(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]
    tag_mod_2 = test_collection_export.tags["tag_mod_2"]

    # export multiple tags overlapping
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(
            tag_ids=[
                tag_1_of_4.tag_id,
                tag_4_of_4.tag_id,
                tag_mod_2.tag_id,
            ]
        ),
    )
    assert len(samples_exported) == samples_total - len(
        {s.sample_id for s in (tag_1_of_4.samples + tag_4_of_4.samples + tag_mod_2.samples)}
    )


def test_export__exclude_single_annotation_tag(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]

    # export single tag
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[anno_tag_1_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 3)


def test_export__exclude_by_multiple_annotation_tags(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples = test_collection_export.samples
    annotations = test_collection_export.annotations
    annotations_total = len(annotations)
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]
    anno_tag_4_of_4 = test_collection_export.tags["anno_tag_4_of_4"]

    # export multiple tags
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[anno_tag_1_of_4.tag_id, anno_tag_4_of_4.tag_id]),
    )
    # ensure correct samples are included
    for i, sample in enumerate(samples):
        if i >= annotations_total / 4 * 3 and i <= annotations_total / 4 * 3:
            assert sample.file_path_abs in samples_exported


def test_export__exclude_by_multiple_annotation_tags__overlapping(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotations_total = test_collection_export.annotations_total
    samples = test_collection_export.samples
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]
    anno_tag_4_of_4 = test_collection_export.tags["anno_tag_4_of_4"]
    anno_tag_mod_2 = test_collection_export.tags["anno_tag_mod_2"]

    # export multiple tags overlapping
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(
            tag_ids=[
                anno_tag_1_of_4.tag_id,
                anno_tag_4_of_4.tag_id,
                anno_tag_mod_2.tag_id,
            ]
        ),
    )
    # ensure correct samples are included
    for i, sample in enumerate(samples):
        if i >= annotations_total / 4 * 3 and i <= annotations_total / 4 * 3 and i % 2 == 0:
            assert sample.file_path_abs in samples_exported


def test_export__exclude_by_sample_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    sample = test_collection_export.samples[-1]

    # export ALL but this single sample_id
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(sample_ids=[sample.sample_id]),
    )
    assert len(samples_exported) == samples_total - 1


def test_export__exclude_by_multiple_samples(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    samples = test_collection_export.samples

    # export ALL but these multiple sample_ids
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(sample_ids=[sample.sample_id for sample in samples]),
    )
    assert len(samples_exported) == samples_total - len(samples)


# test export exclude annotation_ids
def test_export__exclude_by_annotation_id(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotation = test_collection_export.annotations[0]
    samples = test_collection_export.samples

    # export ALL sample except the first sample because it has the annotation
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(annotation_ids=[annotation.sample_id]),
    )

    # ensure the excluded annotation belongs to the sample
    assert annotation in samples[0].sample.annotations
    # ensure it got excluded
    assert len(samples_exported) == len(samples) - 1
    assert samples[0].file_path_abs not in samples_exported


def test_export__exclude_by_annotation_id__ensure_samples_without_annotations_are_included(
    test_db: Session,
) -> None:
    # collection with three samples, only middle sample has an annotation
    collection = create_collection(session=test_db, collection_name="collection2")
    image1 = create_image(
        session=test_db,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=test_db,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    image3 = create_image(
        session=test_db,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample3.png",
    )
    parrot_label = create_annotation_label(
        session=test_db,
        dataset_id=collection.collection_id,
        label_name="parrot",
    )
    # create annotaitons only for sample 2
    sample2_anno1 = create_annotation(
        session=test_db,
        collection_id=collection.collection_id,
        sample_id=image2.sample_id,
        annotation_label_id=parrot_label.annotation_label_id,
    )
    create_annotation(
        session=test_db,
        collection_id=collection.collection_id,
        sample_id=image3.sample_id,
        annotation_label_id=parrot_label.annotation_label_id,
    )

    # export ALL samples except the one with the annotation.
    # ensure we also export samples without an annotation
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=collection.collection_id,
        exclude=ExportFilter(
            annotation_ids=[
                sample2_anno1.sample_id,
            ]
        ),
    )
    assert len(samples_exported) == 2
    assert image1.file_path_abs in samples_exported
    assert image2.file_path_abs not in samples_exported
    assert image3.file_path_abs in samples_exported


def test_export__exclude_by_multiple_annotation_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotations = test_collection_export.annotations
    samples = test_collection_export.samples

    # export ALL samples except the first two samples
    samples_exported = collection_resolver.export(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(
            annotation_ids=[
                # sample 1 annotations
                annotations[0].sample_id,
                annotations[1].sample_id,
                # sample 2 annotation
                annotations[2].sample_id,
            ]
        ),
    )
    assert len(samples_exported) == len(samples) - 2
    assert samples[0].file_path_abs not in samples_exported
    assert samples[1].file_path_abs not in samples_exported


def test_get_filtered_samples_count__include_single_sample_tag(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    count = collection_resolver.get_filtered_samples_count(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
    )
    assert count == int(samples_total / 4)


def test_get_filtered_samples_count__include_multiple_sample_tags(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]
    count = collection_resolver.get_filtered_samples_count(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[tag_1_of_4.tag_id, tag_4_of_4.tag_id]),
    )
    assert count == int(samples_total / 4 * 2)


def test_get_filtered_samples_count__include_sample_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    sample = test_collection_export.samples[0]
    count = collection_resolver.get_filtered_samples_count(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(sample_ids=[sample.sample_id]),
    )
    assert count == 1


def test_get_filtered_samples_count__include_annotation_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotation = test_collection_export.annotations[0]
    count = collection_resolver.get_filtered_samples_count(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(annotation_ids=[annotation.sample_id]),
    )
    assert count == 1


def test_get_filtered_samples_count__exclude_single_sample_tag(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    count = collection_resolver.get_filtered_samples_count(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
    )
    assert count == int(samples_total / 4 * 3)


def test_get_filtered_samples_count__exclude_sample_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    sample = test_collection_export.samples[0]
    count = collection_resolver.get_filtered_samples_count(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(sample_ids=[sample.sample_id]),
    )
    assert count == samples_total - 1


def test_get_filtered_samples_count__exclude_annotation_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    annotation = test_collection_export.annotations[0]
    count = collection_resolver.get_filtered_samples_count(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(annotation_ids=[annotation.sample_id]),
    )
    assert count == samples_total - 1


def test_get_filtered_samples_count__exclude_multiple_annotation_ids(
    test_db: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples = test_collection_export.samples
    annotations = test_collection_export.annotations
    count = collection_resolver.get_filtered_samples_count(
        session=test_db,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(
            annotation_ids=[
                annotations[0].sample_id,
                annotations[1].sample_id,
                annotations[2].sample_id,
            ]
        ),
    )
    assert count == len(samples) - 2
