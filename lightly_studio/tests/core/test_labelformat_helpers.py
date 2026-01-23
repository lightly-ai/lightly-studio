from typing import Iterable

from labelformat.model.category import Category
from sqlmodel import Session

from lightly_studio.core import labelformat_helpers
from tests import helpers_resolvers


def test_create_label_map(db_session: Session) -> None:
    # Test the creation of new labels and re-use of existing labels
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id

    class TestLabels1:
        def get_categories(self) -> Iterable[Category]:
            return [
                Category(id=0, name="dog"),
                Category(id=1, name="cat"),
            ]

    label_input = TestLabels1()

    label_map_1 = labelformat_helpers.create_label_map(
        session=db_session,
        dataset_id=collection_id,
        input_labels=label_input,
    )

    class TestLabels2:
        def get_categories(self) -> Iterable[Category]:
            return [
                Category(id=0, name="dog"),
                Category(id=1, name="cat"),
                Category(id=2, name="bird"),
            ]

    label_input_2 = TestLabels2()

    label_map_2 = labelformat_helpers.create_label_map(
        session=db_session,
        dataset_id=collection_id,
        input_labels=label_input_2,
    )

    assert len(label_map_1) == 2  # dog and cat
    assert len(label_map_2) == 3  # dog, cat and bird

    # Compare label IDs for:
    assert label_map_2[0] == label_map_1[0]  # dog exists already
    assert label_map_2[1] == label_map_1[1]  # cat exists already
    assert label_map_2[2] not in label_map_1.values()  # bird is new
