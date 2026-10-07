import pytest
from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from lightly_studio.services import sampling_service
from tests import helpers_resolvers


def test_validate_preselection(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    image_a = helpers_resolvers.create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/a.png"
    )
    image_b = helpers_resolvers.create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/b.png"
    )
    tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=collection.collection_id, tag_name="preselected"
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[image_a.sample_id]
    )

    tag_name = sampling_service.validate_preselection(
        session=db_session,
        collection_id=collection.collection_id,
        preselected_tag_id=tag.tag_id,
        input_sample_ids=[image_a.sample_id, image_b.sample_id],
        n_samples_to_select=1,
    )

    assert tag_name == "preselected"


def test_validate_preselection__tag_with_annotation_samples(db_session: Session) -> None:
    # Tags have no kind, so a tag of the image collection can hold annotation samples.
    # The subset check rejects it because annotations are never sampling candidates.
    collection = helpers_resolvers.create_collection(session=db_session)
    image = helpers_resolvers.create_image(
        session=db_session, collection_id=collection.collection_id
    )
    label = helpers_resolvers.create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )
    (annotation,) = helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )
    tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=collection.collection_id, tag_name="annotations"
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session, tag_id=tag.tag_id, sample_ids=[annotation.sample_id]
    )

    with pytest.raises(ValueError, match="must match the current filters"):
        sampling_service.validate_preselection(
            session=db_session,
            collection_id=collection.collection_id,
            preselected_tag_id=tag.tag_id,
            input_sample_ids=[image.sample_id],
            n_samples_to_select=1,
        )


def test_validate_preselection__tag_of_other_collection(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    other_collection = helpers_resolvers.create_collection(session=db_session)
    image = helpers_resolvers.create_image(
        session=db_session, collection_id=collection.collection_id
    )
    tag = helpers_resolvers.create_tag(
        session=db_session, collection_id=other_collection.collection_id
    )

    with pytest.raises(ValueError, match="Invalid preselected sample tag"):
        sampling_service.validate_preselection(
            session=db_session,
            collection_id=collection.collection_id,
            preselected_tag_id=tag.tag_id,
            input_sample_ids=[image.sample_id],
            n_samples_to_select=1,
        )
