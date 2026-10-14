"""Tests for updating cuboid_3d geometry of an annotation."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DCreate
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.create_annotation import AnnotationCreateParams
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate


def test_update_annotation__cuboid_3d_geometry(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    """Updating cuboid geometry persists the new values."""
    annotation = annotations_service.create_annotation(
        session=db_session,
        annotation=AnnotationCreateParams(
            annotation_label_id=annotation_labels[0].annotation_label_id,
            annotation_type=AnnotationType.CUBOID_3D,
            collection_id=collection.collection_id,
            parent_sample_id=samples[0].sample_id,
            cuboid_3d=Cuboid3DCreate(
                frame_id="odom",
                px=1.0,
                py=0.0,
                pz=0.5,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=2.0,
                sy=1.0,
                sz=1.5,
            ),
        ),
    )

    result = annotations_service.update_annotation(
        session=db_session,
        annotation_update=AnnotationUpdate(
            annotation_id=annotation.sample_id,
            collection_id=annotation.annotation_collection_id,
            cuboid_3d=Cuboid3DCreate(
                frame_id="map",
                px=3.0,
                py=4.0,
                pz=5.0,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=6.0,
                sy=7.0,
                sz=8.0,
            ),
        ),
    )

    assert result.cuboid_3d_details is not None
    assert result.cuboid_3d_details.frame_id == "map"
    assert result.cuboid_3d_details.px == 3.0
    assert result.cuboid_3d_details.py == 4.0
    assert result.cuboid_3d_details.pz == 5.0
    assert result.cuboid_3d_details.sx == 6.0
    assert result.cuboid_3d_details.sy == 7.0
    assert result.cuboid_3d_details.sz == 8.0


def test_update_annotation__cuboid_3d_type_mismatch(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    """Updating cuboid geometry on a non-cuboid annotation raises ValueError."""
    annotation = annotations_service.create_annotation(
        session=db_session,
        annotation=AnnotationCreateParams(
            annotation_label_id=annotation_labels[0].annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            collection_id=collection.collection_id,
            parent_sample_id=samples[0].sample_id,
            x=10,
            y=20,
            width=30,
            height=40,
        ),
    )

    with pytest.raises(ValueError, match="does not support cuboid_3d"):
        annotations_service.update_annotation(
            session=db_session,
            annotation_update=AnnotationUpdate(
                annotation_id=annotation.sample_id,
                collection_id=annotation.annotation_collection_id,
                cuboid_3d=Cuboid3DCreate(
                    frame_id="odom",
                    px=1.0,
                    py=0.0,
                    pz=0.5,
                    qx=0.0,
                    qy=0.0,
                    qz=0.0,
                    qw=1.0,
                    sx=2.0,
                    sy=1.0,
                    sz=1.5,
                ),
            ),
        )


def test_update_annotation__cuboid_label_only(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
) -> None:
    """Updating only the label on a cuboid annotation succeeds without geometry."""
    annotation = annotations_service.create_annotation(
        session=db_session,
        annotation=AnnotationCreateParams(
            annotation_label_id=annotation_labels[0].annotation_label_id,
            annotation_type=AnnotationType.CUBOID_3D,
            collection_id=collection.collection_id,
            parent_sample_id=samples[0].sample_id,
            cuboid_3d=Cuboid3DCreate(
                frame_id="odom",
                px=1.0,
                py=0.0,
                pz=0.5,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                sx=2.0,
                sy=1.0,
                sz=1.5,
            ),
        ),
    )

    result = annotations_service.update_annotation(
        session=db_session,
        annotation_update=AnnotationUpdate(
            annotation_id=annotation.sample_id,
            collection_id=annotation.annotation_collection_id,
            label_name=annotation_labels[1].annotation_label_name,
        ),
    )

    assert result.annotation_label_id == annotation_labels[1].annotation_label_id
    assert result.cuboid_3d_details is not None
    assert result.cuboid_3d_details.frame_id == "odom"
    assert result.cuboid_3d_details.px == 1.0
