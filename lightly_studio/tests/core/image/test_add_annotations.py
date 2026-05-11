from __future__ import annotations

from pathlib import Path

from labelformat.formats.labelformat import LabelformatObjectDetectionInput
from labelformat.model.bounding_box import BoundingBox
from labelformat.model.category import Category
from labelformat.model.image import Image
from labelformat.model.object_detection import ImageObjectDetection, SingleObjectDetection
from sqlmodel import Session

from lightly_studio.core.image import add_annotations
from lightly_studio.resolvers import annotation_resolver, image_resolver
from tests import helpers_resolvers
from tests.helpers_resolvers import ImageStub


def test_add_annotations_from_labelformat__resolved_path_and_collection_name(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(db_session)
    images = helpers_resolvers.create_images(
        db_session,
        collection.collection_id,
        [
            ImageStub(
                path=str(Path("images/image.jpg").absolute()),
                width=100,
                height=200,
            ),
        ],
    )
    label_input = _get_labelformat_input_obj_det(filename="image.jpg")

    missing_paths = add_annotations.add_annotations_from_labelformat(
        session=db_session,
        root_collection_id=collection.collection_id,
        input_labels=label_input,
        images_root="images",
        collection_name="model_v1",
    )

    annotations = annotation_resolver.get_all_by_collection_name(
        session=db_session,
        collection_name="model_v1",
        parent_collection_id=collection.collection_id,
    ).annotations
    assert missing_paths == []
    assert len(annotations) == 1
    assert annotations[0].parent_sample_id == images[0].sample_id
    assert annotations[0].annotation_label.annotation_label_name == "dog"


def test_add_annotations_from_labelformat__missing_images(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(db_session)
    label_input = _get_labelformat_input_obj_det(filename="nonexistent.jpg")

    missing_paths = add_annotations.add_annotations_from_labelformat(
        session=db_session,
        root_collection_id=collection.collection_id,
        input_labels=label_input,
        images_root="/images",
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    ).samples
    assert missing_paths == ["/images/nonexistent.jpg"]
    assert len(samples) == 0


def _get_labelformat_input_obj_det(filename: str) -> LabelformatObjectDetectionInput:
    categories = [Category(id=0, name="dog")]
    image = Image(id=0, filename=filename, width=100, height=200)
    objects = [
        SingleObjectDetection(
            category=categories[0],
            box=BoundingBox(xmin=10.0, ymin=20.0, xmax=30.0, ymax=40.0),
        ),
    ]
    return LabelformatObjectDetectionInput(
        categories=categories,
        images=[image],
        labels=[ImageObjectDetection(image=image, objects=objects)],
    )
