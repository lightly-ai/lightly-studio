from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import annotation_resolver, tag_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
    create_tag,
)


def test_move_to_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    target = create_collection(
        session=db_session,
        collection_name="reviewed",
        parent_collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    box, mask = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                x=1,
                y=2,
                width=3,
                height=4,
            ),
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=AnnotationType.SEGMENTATION_MASK,
                segmentation_mask=[1, 2, 3, 4],
            ),
        ],
        collection_name="predictions",
    )
    box_id, mask_id = box.sample_id, mask.sample_id
    tag = create_tag(session=db_session, collection_id=box.annotation_collection_id)
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[box_id]
    )

    annotation_resolver.move_to_collection(
        session=db_session, annotation_ids=[box_id, mask_id], collection_id=target.collection_id
    )

    moved_box = annotation_resolver.get_by_id(session=db_session, annotation_id=box_id)
    assert moved_box is not None
    assert moved_box.annotation_collection_id == target.collection_id
    assert moved_box.object_detection_details is not None
    details = moved_box.object_detection_details
    assert (details.x, details.y, details.width, details.height) == (1, 2, 3, 4)
    # The tag link moves to a tag with the same name in the target collection.
    assert [(t.name, t.collection_id) for t in moved_box.sample.tags] == [
        ("example_tag", target.collection_id)
    ]
    moved_mask = annotation_resolver.get_by_id(session=db_session, annotation_id=mask_id)
    assert moved_mask is not None
    assert moved_mask.annotation_collection_id == target.collection_id
    assert moved_mask.segmentation_details is not None
    assert moved_mask.segmentation_details.segmentation_mask == [1, 2, 3, 4]
