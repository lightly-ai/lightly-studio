"""Tests for the embeddings2d endpoint."""

from __future__ import annotations

import json

import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from pyarrow import ipc
from sqlmodel import Session

from lightly_studio.dataset.mobileclip_embedding_generator import EMBEDDING_DIMENSION
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    image_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    fill_db_with_samples_and_embeddings,
)


def test_get_embeddings2d__with_metadata_field_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 4

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    cities = ["Paris", "London", "Paris"]
    for sample, city in zip(samples[:3], cities):
        sample.sample["city"] = city
    samples[3].sample["weather"] = "rain"  # Missing value

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "city"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    color_categories = table.column("color_categories").to_pylist()

    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]  # Paris
    assert sample_id_to_colors[str(samples[1].sample_id)] == [2]  # London
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3]  # Paris
    assert sample_id_to_colors[str(samples[3].sample_id)] == []  # Unassigned

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["0"] == "Filtered out"
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "London"
    assert legend["3"] == "Paris"


def test_get_embeddings2d__with_mixed_type_metadata_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Mixed-type metadata values for the same key return a 400 error."""
    n_samples = 2

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    samples[0].sample["score"] = "high"
    samples[1].sample["score"] = False

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "score"},
        },
    )

    assert response.status_code == 400
    assert "does not match schema type" in response.json()["error"]


def test_get_embeddings2d__with_boolean_metadata_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 3

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    # Samples[0] and samples[2] -> False, samples[1] -> True.
    flags = [False, True, False]
    for sample, flag in zip(samples, flags):
        sample.sample["is_sunny"] = flag

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "is_sunny"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    color_categories = table.column("color_categories").to_pylist()

    # False is sorted before True, so False -> cat 2, True -> cat 3.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [2]  # False -> cat 2
    assert sample_id_to_colors[str(samples[1].sample_id)] == [3]  # True -> cat 3
    assert sample_id_to_colors[str(samples[2].sample_id)] == [2]  # False -> cat 2

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["0"] == "Filtered out"
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "false"
    assert legend["3"] == "true"


def test_get_embeddings2d__with_integer_metadata_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 3

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    scores = [10, 30, 20]
    for sample, score in zip(samples, scores):
        sample.sample["score"] = score

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "score"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    color_categories = table.column("color_categories").to_pylist()

    # Values are sorted numerically: 10 -> cat 2, 20 -> cat 3, 30 -> cat 4.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [2]  # score=10
    assert sample_id_to_colors[str(samples[1].sample_id)] == [4]  # score=30
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3]  # score=20

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["0"] == "Filtered out"
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "10"
    assert legend["3"] == "20"
    assert legend["4"] == "30"


def test_get_embeddings2d__with_integer_metadata_color_by__buckets_when_more_than_50_unique_values(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """When there are more than 50 unique integer values, values are grouped into buckets."""
    n_samples = 100

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    for i, sample in enumerate(samples):
        sample.sample["score"] = i  # scores 0..99

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "score"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    color_categories = table.column("color_categories").to_pylist()

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["0"] == "Filtered out"
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "0-1"
    assert legend["51"] == "98-99"
    assert len(legend) == 52  # 2 reserved + 50 buckets

    # score=0 and score=1 share bucket "0-1" -> same category.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [2]  # score=0 -> bucket "0-1"
    assert sample_id_to_colors[str(samples[1].sample_id)] == [2]  # score=1 -> bucket "0-1"
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3]  # score=2 -> bucket "2-3"
    assert sample_id_to_colors[str(samples[99].sample_id)] == [51]  # score=99 -> bucket "98-99"


def test_get_embeddings2d__with_metadata_field_color_by_and_sample_ids_filter(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 4

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    cities = ["Paris", "London", "Rome", "Berlin"]
    for sample, city in zip(samples, cities):
        sample.sample["city"] = city

    selected_samples = [samples[0], samples[2]]
    selected_sample_ids = [sample.sample_id for sample in selected_samples]

    image_filter = ImageFilter(
        sample_filter=SampleFilter(sample_ids=selected_sample_ids),
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": image_filter.model_dump(mode="json"),
            "color_by": {"type": "metadata_field", "key": "city"},
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    color_categories = table.column("color_categories").to_pylist()

    assert len(sample_ids_payload) == len(fulfils_filter)
    assert len(sample_ids_payload) == len(color_categories)

    sample_id_to_filter = dict(zip(sample_ids_payload, fulfils_filter))

    assert sample_id_to_filter[str(samples[0].sample_id)] == 1
    assert sample_id_to_filter[str(samples[1].sample_id)] == 0
    assert sample_id_to_filter[str(samples[2].sample_id)] == 1
    assert sample_id_to_filter[str(samples[3].sample_id)] == 0

    # Color categories are filter-unaware: every sample reports its own category.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [4]  # Paris
    assert sample_id_to_colors[str(samples[1].sample_id)] == [3]  # London
    assert sample_id_to_colors[str(samples[2].sample_id)] == [5]  # Rome
    assert sample_id_to_colors[str(samples[3].sample_id)] == [2]  # Berlin

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["0"] == "Filtered out"
    assert legend["1"] == "Unassigned"
    assert legend["2"] == "Berlin"
    assert legend["3"] == "London"
    assert legend["4"] == "Paris"
    assert legend["5"] == "Rome"


@pytest.mark.parametrize(
    "value",
    [
        {"a": 1},
        [1, 2, 3],
        1.5,
    ],
)
def test_get_embeddings2d__with_unsupported_metadata_color_by(
    value: object,
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Unsupported metadata value types return a 400 error."""
    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=1,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples

    samples[0].sample["info"] = value

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {"type": "metadata_field", "key": "info"},
        },
    )

    assert response.status_code == 400
    assert "unsupported type" in response.json()["error"]


def test_get_embeddings2d__with_tag_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 5

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    tag_a = tag_resolver.create(
        session=db_session,
        tag=TagCreate(collection_id=collection_id, name="alpha", kind="sample"),
    )
    tag_b = tag_resolver.create(
        session=db_session,
        tag=TagCreate(collection_id=collection_id, name="beta", kind="sample"),
    )

    # samples[0] in alpha only, samples[1] in beta only,
    # samples[2] in both, samples[3,4] untagged.
    tag_resolver.add_tag_to_sample(
        session=db_session, tag_id=tag_a.tag_id, sample=samples[0].sample
    )
    tag_resolver.add_tag_to_sample(
        session=db_session, tag_id=tag_a.tag_id, sample=samples[2].sample
    )
    tag_resolver.add_tag_to_sample(
        session=db_session, tag_id=tag_b.tag_id, sample=samples[1].sample
    )
    tag_resolver.add_tag_to_sample(
        session=db_session, tag_id=tag_b.tag_id, sample=samples[2].sample
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {
                "type": "tag",
                "tag_ids": [str(tag_a.tag_id), str(tag_b.tag_id)],
            },
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()

    assert table.schema.field("color_categories").type == pa.list_(pa.uint8())
    color_categories = table.column("color_categories").to_pylist()
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [2]  # alpha
    assert sample_id_to_colors[str(samples[1].sample_id)] == [3]  # beta
    assert sample_id_to_colors[str(samples[2].sample_id)] == [2, 3]  # both, sorted
    assert sample_id_to_colors[str(samples[3].sample_id)] == []  # untagged
    assert sample_id_to_colors[str(samples[4].sample_id)] == []  # untagged

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {
        "0": "Filtered out",
        "1": "Unassigned",
        "2": "alpha",
        "3": "beta",
    }


def test_get_embeddings2d__with_tag_color_by_and_filter(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 4

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    tag_color = tag_resolver.create(
        session=db_session,
        tag=TagCreate(collection_id=collection_id, name="color_tag", kind="sample"),
    )
    tag_filter = tag_resolver.create(
        session=db_session,
        tag=TagCreate(collection_id=collection_id, name="filter_tag", kind="sample"),
    )

    # All samples get the color tag.
    for sample in samples:
        tag_resolver.add_tag_to_sample(
            session=db_session, tag_id=tag_color.tag_id, sample=sample.sample
        )
    # Only first two get the filter tag.
    tag_resolver.add_tag_to_sample(
        session=db_session, tag_id=tag_filter.tag_id, sample=samples[0].sample
    )
    tag_resolver.add_tag_to_sample(
        session=db_session, tag_id=tag_filter.tag_id, sample=samples[1].sample
    )

    image_filter = ImageFilter(
        sample_filter=SampleFilter(tag_ids=[tag_filter.tag_id]),
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": image_filter.model_dump(mode="json"),
            "color_by": {
                "type": "tag",
                "tag_ids": [str(tag_color.tag_id)],
            },
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    color_categories = table.column("color_categories").to_pylist()

    # First two pass the filter, last two are filtered out.
    sample_id_to_filter = dict(zip(sample_ids_payload, fulfils_filter))
    assert sample_id_to_filter[str(samples[0].sample_id)] == 1
    assert sample_id_to_filter[str(samples[1].sample_id)] == 1
    assert sample_id_to_filter[str(samples[2].sample_id)] == 0
    assert sample_id_to_filter[str(samples[3].sample_id)] == 0

    # All samples have the color tag → category 2, independent of the filter.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [2]
    assert sample_id_to_colors[str(samples[1].sample_id)] == [2]
    assert sample_id_to_colors[str(samples[2].sample_id)] == [2]
    assert sample_id_to_colors[str(samples[3].sample_id)] == [2]

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {
        "0": "Filtered out",
        "1": "Unassigned",
        "2": "color_tag",
    }


def test_get_embeddings2d__with_annotation_color_by(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 5

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )

    # samples[0] has "cat", samples[1] has "dog",
    # samples[2] has both, samples[3,4] unannotated.
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=samples[0].sample_id,
        annotation_label_id=label_cat.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=samples[1].sample_id,
        annotation_label_id=label_dog.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=samples[2].sample_id,
        annotation_label_id=label_cat.annotation_label_id,
    )
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=samples[2].sample_id,
        annotation_label_id=label_dog.annotation_label_id,
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": {},
            "color_by": {
                "type": "annotation",
                "annotation_label_ids": [
                    str(label_cat.annotation_label_id),
                    str(label_dog.annotation_label_id),
                ],
            },
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()

    color_categories = table.column("color_categories").to_pylist()
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [2]  # cat
    assert sample_id_to_colors[str(samples[1].sample_id)] == [3]  # dog
    assert sample_id_to_colors[str(samples[2].sample_id)] == [2, 3]  # both, sorted
    assert sample_id_to_colors[str(samples[3].sample_id)] == []  # unannotated
    assert sample_id_to_colors[str(samples[4].sample_id)] == []  # unannotated

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {
        "0": "Filtered out",
        "1": "Unassigned",
        "2": "cat",
        "3": "dog",
    }


def test_get_embeddings2d__with_annotation_color_by_and_filter(
    test_client: TestClient,
    db_session: Session,
) -> None:
    n_samples = 4

    collection_id = fill_db_with_samples_and_embeddings(
        session=db_session,
        n_samples=n_samples,
        embedding_model_names=["model_a"],
        embedding_dimension=EMBEDDING_DIMENSION,
    )

    samples = image_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=collection_id,
    ).samples
    assert len(samples) == n_samples

    label = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="cat"
    )

    # All samples get annotated.
    for sample in samples:
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=sample.sample_id,
            annotation_label_id=label.annotation_label_id,
        )

    # Only first two pass the filter.
    selected_sample_ids = [samples[0].sample_id, samples[1].sample_id]
    image_filter = ImageFilter(
        sample_filter=SampleFilter(sample_ids=selected_sample_ids),
    )

    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": image_filter.model_dump(mode="json"),
            "color_by": {
                "type": "annotation",
                "annotation_label_ids": [str(label.annotation_label_id)],
            },
        },
    )

    assert response.status_code == 200

    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    sample_ids_payload = table.column("sample_id").to_pylist()
    fulfils_filter = table.column("fulfils_filter").to_numpy(zero_copy_only=False)
    color_categories = table.column("color_categories").to_pylist()

    # First two pass the filter, last two are filtered out.
    sample_id_to_filter = dict(zip(sample_ids_payload, fulfils_filter))
    assert sample_id_to_filter[str(samples[0].sample_id)] == 1
    assert sample_id_to_filter[str(samples[1].sample_id)] == 1
    assert sample_id_to_filter[str(samples[2].sample_id)] == 0
    assert sample_id_to_filter[str(samples[3].sample_id)] == 0

    # All samples have the label → category 2, independent of the filter.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [2]
    assert sample_id_to_colors[str(samples[1].sample_id)] == [2]
    assert sample_id_to_colors[str(samples[2].sample_id)] == [2]
    assert sample_id_to_colors[str(samples[3].sample_id)] == [2]

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {"0": "Filtered out", "1": "Unassigned", "2": "cat"}
