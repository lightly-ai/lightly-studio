from sqlmodel import Session

from lightly_studio.core import labelformat_helpers
from tests import helpers_resolvers
from tests.helpers_labelformat import get_labelformat_input_obj_det


def test_create_label_map(db_session: Session) -> None:
    # Test the creation of new labels and re-use of existing labels
    collection_id = helpers_resolvers.create_collection(session=db_session).collection_id
    label_input = get_labelformat_input_obj_det(filename="image.jpg", category_names=["dog", "cat"])

    label_map_1 = labelformat_helpers.create_label_map(
        session=db_session,
        dataset_id=collection_id,
        input_labels=label_input,
    )

    label_input_2 = get_labelformat_input_obj_det(
        filename="image.jpg", category_names=["dog", "cat", "bird"]
    )

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
