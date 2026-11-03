from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import image_resolver, tag_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
    SourceLabelPair,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.annotation_count_types import SourceLabelCount
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)


def test_count_image_annotations_by_source__counts_per_source(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    deer = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="deer"
    ).annotation_label_id
    source_ids = _annotate(
        session=db_session,
        collection_id=collection_id,
        rows=[("/a", "ground_truth", deer), ("/b", "ground_truth", deer), ("/c", "model_v1", deer)],
    )

    counts = image_resolver.count_image_annotations_by_source(
        session=db_session, collection_id=collection_id
    )

    assert _as_dict(counts) == {
        (source_ids["ground_truth"], "deer"): (2, 2),
        (source_ids["model_v1"], "deer"): (1, 1),
    }
    assert {count.annotation_label_id for count in counts} == {deer}


def test_count_image_annotations_by_source__current_counts_follow_tag_filter(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    deer = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="deer"
    ).annotation_label_id
    source_ids = _annotate(
        session=db_session,
        collection_id=collection_id,
        rows=[("/a", "ground_truth", deer), ("/b", "ground_truth", deer), ("/c", "model_v1", deer)],
    )
    tag = create_tag(session=db_session, collection_id=collection_id, tag_name="picked")
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[source_ids["/a"]]
    )

    counts = image_resolver.count_image_annotations_by_source(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id])),
    )

    assert _as_dict(counts) == {
        (source_ids["ground_truth"], "deer"): (1, 2),
        (source_ids["model_v1"], "deer"): (0, 1),
    }


def test_count_image_annotations_by_source__own_pairs_do_not_shrink_counts(
    db_session: Session,
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    deer = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="deer"
    ).annotation_label_id
    raccoon = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="raccoon"
    ).annotation_label_id
    source_ids = _annotate(
        session=db_session,
        collection_id=collection_id,
        rows=[("/a", "ground_truth", deer), ("/b", "model_v1", raccoon)],
    )

    counts = image_resolver.count_image_annotations_by_source(
        session=db_session,
        collection_id=collection_id,
        image_filter=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    source_label_pairs=[
                        SourceLabelPair(
                            collection_id=source_ids["ground_truth"], annotation_label_id=deer
                        )
                    ]
                )
            )
        ),
    )

    assert _as_dict(counts) == {
        (source_ids["ground_truth"], "deer"): (1, 1),
        (source_ids["model_v1"], "raccoon"): (1, 1),
    }


def _annotate(
    session: Session, collection_id: UUID, rows: list[tuple[str, str, UUID]]
) -> dict[str, UUID]:
    """Create one image per row with one annotation.

    Returns the source IDs by source name and the image sample IDs by path.
    """
    ids: dict[str, UUID] = {}
    for path, source, label_id in rows:
        image = create_image(session=session, collection_id=collection_id, file_path_abs=path)
        annotation = create_annotation(
            session=session,
            collection_id=collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label_id,
            annotation_collection_name=source,
        )
        ids[source] = annotation.annotation_collection_id
        ids[path] = image.sample_id
    return ids


def _as_dict(counts: list[SourceLabelCount]) -> dict[tuple[UUID, str], tuple[int, int]]:
    return {
        (count.annotation_collection_id, count.label_name): (
            count.current_count,
            count.total_count,
        )
        for count in counts
    }
