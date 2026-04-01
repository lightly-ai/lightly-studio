from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.core.image.image_sample import ImageSample
from tests.helpers_resolvers import create_image


def test_update_metadata() -> None:
    dataset = ImageDataset.create(name="update_metadata_dataset1")
    img1 = create_image(
        session=dataset.session, collection_id=dataset.collection_id, file_path_abs="img1.jpg"
    )
    img2 = create_image(
        session=dataset.session, collection_id=dataset.collection_id, file_path_abs="img2.jpg"
    )
    samples = [ImageSample(img1), ImageSample(img2)]

    samples[0].metadata["key1"] = "value_to_overwrite"
    sample_metadata: list[tuple[UUID, Mapping[str, Any]]] = [
        (samples[0].sample_id, {"key1": "val1", "key2": 2}),
        (samples[1].sample_id, {"key3": 3.5}),
    ]
    dataset.update_metadata(sample_metadata)

    # Verify updates.
    samples = list(dataset)
    # The order might not be guaranteed by list(dataset) unless we use order_by.
    id_to_sample = {s.sample_id: s for s in samples}
    s1 = id_to_sample[img1.sample_id]
    s2 = id_to_sample[img2.sample_id]

    assert s1.metadata["key1"] == "val1"
    assert s1.metadata["key2"] == 2
    assert s2.metadata["key3"] == 3.5


def test_update_metadata__empty() -> None:
    dataset = ImageDataset.create(name="update_metadata_empty_dataset")
    dataset.update_metadata([])  # Should not raise anything.
