"""The Python client loads, filters, iterates and tags a dataset in local and remote mode."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from lightly_studio import ImageDataset
from lightly_studio.core.dataset_query.boolean_expression import AND
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.database import db_manager
from lightly_studio.resolvers import tag_resolver
from tests.helpers_resolvers import create_image, create_tag


@pytest.mark.usefixtures("patch_collection")
@pytest.mark.parametrize("connect_transport", ["local", "remote"], indirect=True)
def test_load_filter_iterate_tag(connect_transport: Callable[[], None]) -> None:
    session = db_manager.persistent_session()
    collection_id = ImageDataset.create(name="my_dataset").collection_id
    images = [
        create_image(session=session, collection_id=collection_id, file_path_abs=path, width=width)
        for path, width in [("/c.png", 300), ("/a.png", 200), ("/b.png", 50), ("/d.png", 400)]
    ]
    cat = create_tag(session=session, collection_id=collection_id, tag_name="cat")
    tag_resolver.add_sample_ids_to_tag_id(
        session=session, tag_id=cat.tag_id, sample_ids=[image.sample_id for image in images[:3]]
    )
    connect_transport()

    dataset = ImageDataset.load(name="my_dataset")
    query = dataset.match(AND(ImageSampleField.width > 100, ImageSampleField.tags.contains("cat")))
    samples = query.order_by(OrderByField(ImageSampleField.file_name)).to_list()
    assert [sample.file_name for sample in samples] == ["a.png", "c.png"]
    query.add_tag("wide_cat")
    samples[0].add_tag("checked")
    samples[1].add_tag("checked")
    samples[1].remove_tag("checked")

    result = [
        (sample.file_name, sample.width, sample.tags)
        for sample in dataset.order_by(OrderByField(ImageSampleField.file_name))
    ]
    assert result == [
        ("a.png", 200, {"cat", "wide_cat", "checked"}),
        ("b.png", 50, {"cat"}),
        ("c.png", 300, {"cat", "wide_cat"}),
        ("d.png", 400, set()),
    ]
