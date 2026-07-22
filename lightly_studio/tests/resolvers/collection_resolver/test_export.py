from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.models.image import ImageTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import collection_resolver, sample_embedding_resolver, tag_resolver
from lightly_studio.resolvers.collection_resolver.export import ExportFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_samples_with_embeddings,
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


def test_export__include_sample_ids__exceeds_postgres_param_limit(db_session: Session) -> None:
    # More sample ids than PostgreSQL's 65,535-parameter cap.
    collection_id = create_collection(session=db_session).collection_id
    image = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/match.png"
    )
    sample_ids = [uuid4() for _ in range(70_000)]
    sample_ids.append(image.sample_id)

    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        include=ExportFilter(sample_ids=sample_ids),
    )

    assert samples_exported == [image.file_path_abs]


def test_export__include_annotation_ids__exceeds_postgres_param_limit(
    db_session: Session,
) -> None:
    # More annotation ids than PostgreSQL's 65,535-parameter cap.
    collection_id = create_collection(session=db_session).collection_id
    image = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/match.png"
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_ids = [uuid4() for _ in range(70_000)]
    annotation_ids.append(annotation.sample_id)

    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        include=ExportFilter(annotation_ids=annotation_ids),
    )

    assert samples_exported == [image.file_path_abs]


def test_export__exclude_sample_ids__exceeds_postgres_param_limit(db_session: Session) -> None:
    # More sample ids than PostgreSQL's 65,535-parameter cap.
    collection_id = create_collection(session=db_session).collection_id
    image = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/match.png"
    )
    sample_ids = [uuid4() for _ in range(70_000)]

    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        exclude=ExportFilter(sample_ids=sample_ids),
    )

    assert samples_exported == [image.file_path_abs]


def test_export__exclude_annotation_ids__exceeds_postgres_param_limit(
    db_session: Session,
) -> None:
    # More annotation ids than PostgreSQL's 65,535-parameter cap.
    collection_id = create_collection(session=db_session).collection_id
    image = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/match.png"
    )
    label = create_annotation_label(session=db_session, root_collection_id=collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_ids = [uuid4() for _ in range(70_000)]
    annotation_ids.append(annotation.sample_id)

    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        exclude=ExportFilter(annotation_ids=annotation_ids),
    )

    assert samples_exported == []


@pytest.fixture
def test_collection_export(db_session: Session) -> TestcollectionExport:
    samples_total = 20
    annotations_per_sample = 2
    annotations_total = samples_total * annotations_per_sample

    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # create annotation_tag
    cat_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )
    dog_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )

    # create samples and an annotation per sample
    images = []
    annotations = []
    for i in range(samples_total):
        image = create_image(
            session=db_session,
            collection_id=collection_id,
            file_path_abs=f"/path/to/sample{i}.png",
        )
        images.append(image)

        # add annotations per sample
        for a in range(annotations_per_sample):
            annotations.append(
                create_annotation(
                    session=db_session,
                    collection_id=collection_id,
                    sample_id=image.sample_id,
                    annotation_label_id=cat_label.annotation_label_id
                    if a % 2 == 0
                    else dog_label.annotation_label_id,
                )
            )

    # create sample tags
    tag_1_of_4 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="tag 1/4",
        kind="sample",
    )
    tag_4_of_4 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="tag 4/4",
        kind="sample",
    )
    tag_mod_2 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="tag mmod2",
        kind="sample",
    )

    # create tags for annotations
    anno_tag_1_of_4 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="anno tag 1/4",
        kind="annotation",
    )
    anno_tag_4_of_4 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="anno tag 4/4",
        kind="annotation",
    )
    anno_tag_mod_2 = create_tag(
        session=db_session,
        collection_id=collection_id,
        tag_name="anno tag mmod2",
        kind="annotation",
    )

    # add samples to tags
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_1_of_4.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i < samples_total / 4],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_4_of_4.tag_id,
        sample_ids=[
            sample.sample_id for i, sample in enumerate(images) if i >= samples_total / 4 * 3
        ],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_mod_2.tag_id,
        sample_ids=[sample.sample_id for i, sample in enumerate(images) if i % 2 == 0],
    )

    # add annotations to tags
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=anno_tag_1_of_4.tag_id,
        sample_ids=[
            annotation.sample_id
            for i, annotation in enumerate(annotations)
            if i < annotations_total / 4
        ],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=anno_tag_4_of_4.tag_id,
        sample_ids=[
            annotation.sample_id
            for i, annotation in enumerate(annotations)
            if i >= annotations_total / 4 * 3
        ],
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=anno_tag_mod_2.tag_id,
        sample_ids=[annotation.sample_id for i, annotation in enumerate(annotations) if i % 2 == 0],
    )

    # add second collection to ensure we properly scope it to one collection
    collection2 = create_collection(session=db_session, collection_name="collection2")
    image2 = create_image(
        session=db_session,
        collection_id=collection2.collection_id,
        file_path_abs="/second/collection/sample.png",
    )
    parrot_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection2.collection_id,
        label_name="parrot",
    )
    create_annotation(
        session=db_session,
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
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]

    with pytest.raises(ValueError, match=r"Cannot include and exclude at the same time."):
        collection_resolver.export(
            session=db_session,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
            exclude=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
        )


def test_export__include_or_exclude__none_provided(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    with pytest.raises(ValueError, match=r"Include or exclude filter is required."):
        collection_resolver.export(
            session=db_session, collection_id=test_collection_export.collection.collection_id
        )


def test_export__include_no_empty_list_provided(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    with pytest.raises(ValueError, match=r"List should have at least 1 item"):
        collection_resolver.export(
            session=db_session,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(tag_ids=[]),
        )
    with pytest.raises(ValueError, match=r"List should have at least 1 item"):
        collection_resolver.export(
            session=db_session,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(sample_ids=[]),
        )
    with pytest.raises(ValueError, match=r"List should have at least 1 item"):
        collection_resolver.export(
            session=db_session,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(annotation_ids=[]),
        )


def test_export__include_with_either_tag_ids_or_sample_ids_or_annotation_ids(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    sample = test_collection_export.samples[0]
    annotation = test_collection_export.annotations[0]

    with pytest.raises(
        ValueError,
        match=r"Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        collection_resolver.export(
            session=db_session,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(tag_ids=[tag_1_of_4.tag_id], sample_ids=[sample.sample_id]),
        )

    with pytest.raises(
        ValueError,
        match=r"Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        collection_resolver.export(
            session=db_session,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(
                sample_ids=[sample.sample_id],
                annotation_ids=[annotation.sample_id],
            ),
        )

    with pytest.raises(
        ValueError,
        match=r"Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        collection_resolver.export(
            session=db_session,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(
                annotation_ids=[annotation.sample_id],
                tag_ids=[tag_1_of_4.tag_id],
            ),
        )

    with pytest.raises(
        ValueError,
        match=r"Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        collection_resolver.export(
            session=db_session,
            collection_id=test_collection_export.collection.collection_id,
            include=ExportFilter(
                tag_ids=[tag_1_of_4.tag_id],
                sample_ids=[sample.sample_id],
                annotation_ids=[annotation.sample_id],
            ),
        )


# test export include tags
def test_export__include_single_sample_tag(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]

    # export single tag
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4)


def test_export__include_multiple_sample_tags(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]

    # export multiple tags
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[tag_1_of_4.tag_id, tag_4_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 2)


def test_export__include_multiple_sample_tags__overlapping(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]
    tag_mod_2 = test_collection_export.tags["tag_mod_2"]

    # export multiple tags overlapping
    samples_exported = collection_resolver.export(
        session=db_session,
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
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]

    # export single tag
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[anno_tag_1_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4)


def test_export__include_multiple_annotation_tags(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]
    anno_tag_4_of_4 = test_collection_export.tags["anno_tag_4_of_4"]

    # export multiple tags
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[anno_tag_1_of_4.tag_id, anno_tag_4_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 2)


def test_export__include_multiple_annotation_tags__overlapping(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]
    anno_tag_4_of_4 = test_collection_export.tags["anno_tag_4_of_4"]
    anno_tag_mod_2 = test_collection_export.tags["anno_tag_mod_2"]

    # export multiple tags overlapping
    samples_exported = collection_resolver.export(
        session=db_session,
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
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    sample = test_collection_export.samples[-1]

    # export single sample_id
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(sample_ids=[sample.sample_id]),
    )
    assert len(samples_exported) == 1


def test_export__include_multiple_sample_ids(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples = test_collection_export.samples

    # export single tag
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(sample_ids=[sample.sample_id for sample in samples]),
    )
    assert len(samples_exported) == len(samples)


# test export include annotation_ids
def test_export__include_annotation_id(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotation = test_collection_export.annotations[-1]
    sample = test_collection_export.samples[-1]

    # export sample via single annotation_id
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(annotation_ids=[annotation.sample_id]),
    )
    assert len(samples_exported) == 1
    assert samples_exported[0] == sample.file_path_abs
    assert annotation in sample.sample.annotations


def test_export__include_multiple_annotation_ids(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotations = test_collection_export.annotations
    samples = test_collection_export.samples

    # export sample via multiple annotations preventing duplicates
    samples_exported = collection_resolver.export(
        session=db_session,
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
        match=r"Either tag_ids, sample_ids, or annotation_ids must be set.",
    ):
        ExportFilter(tag_ids=[tag_1_of_4.tag_id], sample_ids=[sample.sample_id])


def test_export__exclude_single_sample_tag(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]

    # export single tag
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 3)


def test_export__exclude_by_multiple_sample_tags(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]

    # export multiple tags
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[tag_1_of_4.tag_id, tag_4_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 2)


def test_export__exclude_by_multiple_sample_tags__overlapping(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]
    tag_mod_2 = test_collection_export.tags["tag_mod_2"]

    # export multiple tags overlapping
    samples_exported = collection_resolver.export(
        session=db_session,
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
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]

    # export single tag
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[anno_tag_1_of_4.tag_id]),
    )
    assert len(samples_exported) == int(samples_total / 4 * 3)


def test_export__exclude_by_multiple_annotation_tags(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples = test_collection_export.samples
    annotations = test_collection_export.annotations
    annotations_total = len(annotations)
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]
    anno_tag_4_of_4 = test_collection_export.tags["anno_tag_4_of_4"]

    # export multiple tags
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[anno_tag_1_of_4.tag_id, anno_tag_4_of_4.tag_id]),
    )
    # ensure correct samples are included
    for i, sample in enumerate(samples):
        if i >= annotations_total / 4 * 3 and i <= annotations_total / 4 * 3:
            assert sample.file_path_abs in samples_exported


def test_export__exclude_by_multiple_annotation_tags__overlapping(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotations_total = test_collection_export.annotations_total
    samples = test_collection_export.samples
    anno_tag_1_of_4 = test_collection_export.tags["anno_tag_1_of_4"]
    anno_tag_4_of_4 = test_collection_export.tags["anno_tag_4_of_4"]
    anno_tag_mod_2 = test_collection_export.tags["anno_tag_mod_2"]

    # export multiple tags overlapping
    samples_exported = collection_resolver.export(
        session=db_session,
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
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    sample = test_collection_export.samples[-1]

    # export ALL but this single sample_id
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(sample_ids=[sample.sample_id]),
    )
    assert len(samples_exported) == samples_total - 1


def test_export__exclude_by_multiple_samples(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    samples = test_collection_export.samples

    # export ALL but these multiple sample_ids
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(sample_ids=[sample.sample_id for sample in samples]),
    )
    assert len(samples_exported) == samples_total - len(samples)


# test export exclude annotation_ids
def test_export__exclude_by_annotation_id(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotation = test_collection_export.annotations[0]
    samples = test_collection_export.samples

    # export ALL sample except the first sample because it has the annotation
    samples_exported = collection_resolver.export(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(annotation_ids=[annotation.sample_id]),
    )

    # ensure the excluded annotation belongs to the sample
    assert annotation in samples[0].sample.annotations
    # ensure it got excluded
    assert len(samples_exported) == len(samples) - 1
    assert samples[0].file_path_abs not in samples_exported


def test_export__exclude_by_annotation_id__ensure_samples_without_annotations_are_included(
    db_session: Session,
) -> None:
    # collection with three samples, only middle sample has an annotation
    collection = create_collection(session=db_session, collection_name="collection2")
    image1 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    image2 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    image3 = create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/path/to/sample3.png",
    )
    parrot_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="parrot",
    )
    # create annotaitons only for sample 2
    sample2_anno1 = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image2.sample_id,
        annotation_label_id=parrot_label.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image3.sample_id,
        annotation_label_id=parrot_label.annotation_label_id,
    )

    # export ALL samples except the one with the annotation.
    # ensure we also export samples without an annotation
    samples_exported = collection_resolver.export(
        session=db_session,
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
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotations = test_collection_export.annotations
    samples = test_collection_export.samples

    # export ALL samples except the first two samples
    samples_exported = collection_resolver.export(
        session=db_session,
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


def test_export__image_filter__tag_ids__returns_intersection(
    db_session: Session,
) -> None:
    # include.tag_ids covers A and B; ImageFilter covers B and C → intersection is B.
    collection_id = create_collection(session=db_session).collection_id
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/b.png"
    )
    image_c = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/c.png"
    )

    tag_ab = create_tag(
        session=db_session, collection_id=collection_id, tag_name="ab", kind="sample"
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag_ab.tag_id,
        sample_ids=[image_a.sample_id, image_b.sample_id],
    )

    image_filter = ImageFilter(
        sample_filter=SampleFilter(sample_ids=[image_b.sample_id, image_c.sample_id])
    )
    result = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        include=ExportFilter(tag_ids=[tag_ab.tag_id]),
        collection_filter=image_filter,
    )

    assert result == [image_b.file_path_abs]


def test_export__image_filter__sample_ids__returns_intersection(
    db_session: Session,
) -> None:
    # include.sample_ids covers A and B; ImageFilter covers B and C → intersection is B.
    collection_id = create_collection(session=db_session).collection_id
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/b.png"
    )
    image_c = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/c.png"
    )

    image_filter = ImageFilter(
        sample_filter=SampleFilter(sample_ids=[image_b.sample_id, image_c.sample_id])
    )
    result = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        include=ExportFilter(sample_ids=[image_a.sample_id, image_b.sample_id]),
        collection_filter=image_filter,
    )

    assert result == [image_b.file_path_abs]


def test_get_filtered_samples_count__include_single_sample_tag(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
    )
    assert count == int(samples_total / 4)


def test_get_filtered_samples_count__include_multiple_sample_tags(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    tag_4_of_4 = test_collection_export.tags["tag_4_of_4"]
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(tag_ids=[tag_1_of_4.tag_id, tag_4_of_4.tag_id]),
    )
    assert count == int(samples_total / 4 * 2)


def test_get_filtered_samples_count__include_sample_ids(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    sample = test_collection_export.samples[0]
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(sample_ids=[sample.sample_id]),
    )
    assert count == 1


def test_get_filtered_samples_count__include_annotation_ids(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    annotation = test_collection_export.annotations[0]
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        include=ExportFilter(annotation_ids=[annotation.sample_id]),
    )
    assert count == 1


def test_get_filtered_samples_count__exclude_single_sample_tag(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    tag_1_of_4 = test_collection_export.tags["tag_1_of_4"]
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(tag_ids=[tag_1_of_4.tag_id]),
    )
    assert count == int(samples_total / 4 * 3)


def test_get_filtered_samples_count__exclude_sample_ids(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    sample = test_collection_export.samples[0]
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(sample_ids=[sample.sample_id]),
    )
    assert count == samples_total - 1


def test_get_filtered_samples_count__exclude_annotation_ids(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples_total = test_collection_export.samples_total
    annotation = test_collection_export.annotations[0]
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=test_collection_export.collection.collection_id,
        exclude=ExportFilter(annotation_ids=[annotation.sample_id]),
    )
    assert count == samples_total - 1


def test_get_filtered_samples_count__exclude_multiple_annotation_ids(
    db_session: Session,
    test_collection_export: TestcollectionExport,
) -> None:
    samples = test_collection_export.samples
    annotations = test_collection_export.annotations
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
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


def test_export__embedding_region_filter__returns_samples_inside_region(
    db_session: Session,
) -> None:
    # Three samples: a=(1,1) and b=(5,5) inside a [0,10]x[0,10] square; c=(100,100) outside.
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_dimension=3,
    )
    image_a, image_b, image_c = create_samples_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="sample_a.png"), [0.1, 0.2, 0.3]),
            (ImageStub(path="sample_b.png"), [1.1, 0.2, 0.3]),
            (ImageStub(path="sample_c.png"), [2.1, 0.2, 0.3]),
        ],
    )
    # Seed 2D coordinates so that a and b are inside the lasso region, c is not.
    cache_key, ordered_sample_ids = sample_embedding_resolver.get_hash_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    coordinates = {
        image_a.sample_id: (1.0, 1.0),
        image_b.sample_id: (5.0, 5.0),
        image_c.sample_id: (100.0, 100.0),
    }
    db_session.add(
        TwoDimEmbeddingTable(
            hash=cache_key,
            x=[coordinates[sid][0] for sid in ordered_sample_ids],
            y=[coordinates[sid][1] for sid in ordered_sample_ids],
        )
    )
    db_session.commit()

    region = EmbeddingRegion(
        polygon=[
            Point2D(x=0, y=0),
            Point2D(x=10, y=0),
            Point2D(x=10, y=10),
            Point2D(x=0, y=10),
        ]
    )
    result = collection_resolver.export(
        session=db_session,
        collection_id=collection_id,
        include=ExportFilter(sample_ids=[image_a.sample_id, image_b.sample_id, image_c.sample_id]),
        collection_filter=ImageFilter(sample_filter=SampleFilter(embedding_region=region)),
    )

    assert sorted(result) == sorted([image_a.file_path_abs, image_b.file_path_abs])


def test_get_filtered_samples_count__embedding_region_filter__returns_count_inside_region(
    db_session: Session,
) -> None:
    # Three samples: a=(1,1) and b=(5,5) inside a [0,10]x[0,10] square; c=(100,100) outside.
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_dimension=3,
    )
    image_a, image_b, image_c = create_samples_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="sample_a.png"), [0.1, 0.2, 0.3]),
            (ImageStub(path="sample_b.png"), [1.1, 0.2, 0.3]),
            (ImageStub(path="sample_c.png"), [2.1, 0.2, 0.3]),
        ],
    )
    # Seed 2D coordinates so that a and b are inside the lasso region, c is not.
    cache_key, ordered_sample_ids = sample_embedding_resolver.get_hash_by_collection_id(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    coordinates = {
        image_a.sample_id: (1.0, 1.0),
        image_b.sample_id: (5.0, 5.0),
        image_c.sample_id: (100.0, 100.0),
    }
    db_session.add(
        TwoDimEmbeddingTable(
            hash=cache_key,
            x=[coordinates[sid][0] for sid in ordered_sample_ids],
            y=[coordinates[sid][1] for sid in ordered_sample_ids],
        )
    )
    db_session.commit()

    region = EmbeddingRegion(
        polygon=[
            Point2D(x=0, y=0),
            Point2D(x=10, y=0),
            Point2D(x=10, y=10),
            Point2D(x=0, y=10),
        ]
    )
    count = collection_resolver.get_filtered_samples_count(
        session=db_session,
        collection_id=collection_id,
        include=ExportFilter(sample_ids=[image_a.sample_id, image_b.sample_id, image_c.sample_id]),
        collection_filter=ImageFilter(sample_filter=SampleFilter(embedding_region=region)),
    )

    assert count == 2
