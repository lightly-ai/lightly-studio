from __future__ import annotations

import pytest

from lightly_studio import ImageDataset
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_image,
)


class TestImageDataset:
    def test_delete_annotation_source(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        image = create_image(session=dataset.session, collection_id=dataset.collection_id)
        label = create_annotation_label(
            session=dataset.session, root_collection_id=dataset.collection_id
        )
        details = AnnotationDetails(
            sample_id=image.sample_id, annotation_label_id=label.annotation_label_id
        )
        create_annotations(
            session=dataset.session,
            collection_id=dataset.collection_id,
            annotations=[details, details],
            collection_name="predictions",
        )

        deleted_count = dataset.delete_annotation_source(annotation_source="predictions")

        assert deleted_count == 2

        source_id = collection_resolver.get_by_name(
            session=dataset.session, name="predictions", parent_collection_id=dataset.collection_id
        )
        assert source_id is None
        assert [sample.annotations for sample in dataset] == [[]]

    def test_delete_annotation_source__unknown_name(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")

        with pytest.raises(ValueError, match="no annotation source 'predictions'"):
            dataset.delete_annotation_source(annotation_source="predictions")

    def test_delete_annotation_source__name_of_other_child(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = ImageDataset.create(name="test_dataset")
        create_collection(
            session=dataset.session,
            collection_name="captions",
            parent_collection_id=dataset.collection_id,
            sample_type=SampleType.CAPTION,
        )

        with pytest.raises(ValueError, match="no annotation source 'captions'"):
            dataset.delete_annotation_source(annotation_source="captions")
