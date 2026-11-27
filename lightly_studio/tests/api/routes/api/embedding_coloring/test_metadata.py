"""Scalar metadata coloring preserves missing values and filter-aware legends."""

from typing import Any

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import metadata
from tests.helpers_resolvers import create_collection, create_image


@pytest.mark.parametrize(
    ("values", "matching_indices", "categories", "legend"),
    [
        (["b", "a", None], None, [[4], [3], []], {3: "a", 4: "b"}),
        (["b", "a", None], [], [[], [], []], {}),
        ([False, True, None], [1], [[], [3], []], {3: "true"}),
        ([0, 10, None], [0], [[3], [4], []], {3: "0", 4: "10"}),
    ],
)
def test_build_metadata_color_maps(
    db_session: Session,
    values: list[Any],
    matching_indices: list[int] | None,
    categories: list[list[int]],
    legend: dict[int, str],
) -> None:
    collection = create_collection(session=db_session)
    images = [
        create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs=f"/image-{index}.jpg",
        )
        for index in range(3)
    ]
    for image, value in zip(images, values):
        if value is not None:
            image.sample["value"] = value
    sample_ids = [image.sample_id for image in images]
    matching_ids = (
        None if matching_indices is None else {sample_ids[index] for index in matching_indices}
    )

    assert metadata.build_metadata_color_maps(
        session=db_session,
        collection_id=collection.collection_id,
        key="value",
        sample_ids=sample_ids,
        matching_sample_ids=matching_ids,
    ) == (categories, legend)
