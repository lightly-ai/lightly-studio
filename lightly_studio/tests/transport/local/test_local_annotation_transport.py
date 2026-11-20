from __future__ import annotations

import uuid

import pytest

from lightly_studio.database import db_manager
from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation.object_track import ObjectTrackCreate
from lightly_studio.resolvers import object_track_resolver
from lightly_studio.transport.annotation_transport import AnnotationTransport
from lightly_studio.transport.local.local_annotation_transport import LocalAnnotationTransport
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


@pytest.mark.usefixtures("patch_collection")
class TestLocalAnnotationTransport:
    def test_get_or_create_labels(self) -> None:
        session = db_manager.persistent_session()
        collection = create_collection(session=session)
        cat = create_annotation_label(
            session=session, root_collection_id=collection.collection_id, label_name="cat"
        )
        transport: AnnotationTransport = LocalAnnotationTransport()

        labels = transport.get_or_create_labels(
            dataset_id=collection.dataset_id, label_names=["dog", "cat", "dog"]
        )

        assert [label.annotation_label_name for label in labels] == ["dog", "cat"]
        assert labels[1].annotation_label_id == cat.annotation_label_id

    def test_get_by_sample_ids(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        annotated = create_image(session=session, collection_id=collection_id)
        create_image(session=session, collection_id=collection_id, file_path_abs="/other.png")
        label = create_annotation_label(session=session, root_collection_id=collection_id)
        annotation = create_annotation(
            session=session,
            collection_id=collection_id,
            sample_id=annotated.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
        transport: AnnotationTransport = LocalAnnotationTransport()

        annotations = transport.get_by_sample_ids(sample_ids=[annotated.sample_id])

        assert [a.sample_id for a in annotations] == [annotation.sample_id]
        assert annotations[0].annotation_label.annotation_label_name == "cat"
        assert annotations[0].object_detection_details is not None

    def test_create(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        label = create_annotation_label(session=session, root_collection_id=collection_id)
        transport: AnnotationTransport = LocalAnnotationTransport()

        annotation_ids = transport.create(
            parent_collection_id=collection_id,
            annotations=[
                AnnotationCreate(
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.CLASSIFICATION,
                    parent_sample_id=image.sample_id,
                )
            ],
            collection_name="gt",
            covered_sample_ids=[],
        )

        annotations = transport.get_by_sample_ids(sample_ids=[image.sample_id])
        assert [a.sample_id for a in annotations] == annotation_ids
        assert annotations[0].annotation_type == AnnotationType.CLASSIFICATION

    def test_delete(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        label = create_annotation_label(session=session, root_collection_id=collection_id)
        annotation = create_annotation(
            session=session,
            collection_id=collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
        transport: AnnotationTransport = LocalAnnotationTransport()

        # An unknown ID stops the delete before it deletes the known annotation.
        with pytest.raises(ValueError, match=r"not found"):
            transport.delete(annotation_ids=[annotation.sample_id, uuid.uuid4()])
        assert len(transport.get_by_sample_ids(sample_ids=[image.sample_id])) == 1

        transport.delete(annotation_ids=[annotation.sample_id])
        assert transport.get_by_sample_ids(sample_ids=[image.sample_id]) == []

    def test_get_free_object_track_numbers(self) -> None:
        session = db_manager.persistent_session()
        dataset_id = create_collection(session=session).dataset_id
        object_track_resolver.create_many(
            session=session,
            tracks=[ObjectTrackCreate(object_track_number=2, dataset_id=dataset_id)],
        )
        transport: AnnotationTransport = LocalAnnotationTransport()

        numbers = transport.get_free_object_track_numbers(dataset_id=dataset_id, count=2)

        assert numbers == [1, 3]

    def test_create_object_tracks(self) -> None:
        session = db_manager.persistent_session()
        dataset_id = create_collection(session=session).dataset_id
        transport: AnnotationTransport = LocalAnnotationTransport()

        track_ids = transport.create_object_tracks(
            tracks=[ObjectTrackCreate(object_track_number=7, dataset_id=dataset_id)]
        )

        track = object_track_resolver.get_by_id(session=session, object_track_id=track_ids[0])
        assert track is not None
        assert track.object_track_number == 7
