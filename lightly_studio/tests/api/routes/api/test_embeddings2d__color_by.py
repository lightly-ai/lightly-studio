"""Tests for the embeddings2d endpoint."""

from __future__ import annotations

import json

import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from pyarrow import ipc
from sqlmodel import Session

from lightly_studio.dataset.mobileclip_embedding_generator import EMBEDDING_DIMENSION
from lightly_studio.models.collection import SampleType
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    collection_resolver,
    image_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
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

    # Values are ranked by frequency: "Paris" (2 samples) before "London" (1).
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]  # Paris
    assert sample_id_to_colors[str(samples[1].sample_id)] == [4]  # London
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3]  # Paris
    assert sample_id_to_colors[str(samples[3].sample_id)] == []  # Unassigned

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["3"] == "Paris"
    assert legend["4"] == "London"


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

    # Values are frequency-ordered: False is in 2 samples, True in 1, so False
    # takes cat 3 and True cat 4.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]  # False -> cat 3
    assert sample_id_to_colors[str(samples[1].sample_id)] == [4]  # True -> cat 4
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3]  # False -> cat 3

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["3"] == "false"
    assert legend["4"] == "true"


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

    # Values are sorted numerically: 10 -> cat 3, 20 -> cat 4, 30 -> cat 5.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]  # score=10
    assert sample_id_to_colors[str(samples[1].sample_id)] == [5]  # score=30
    assert sample_id_to_colors[str(samples[2].sample_id)] == [4]  # score=20

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend["3"] == "10"
    assert legend["4"] == "20"
    assert legend["5"] == "30"


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
    assert legend["3"] == "0-1"
    assert legend["52"] == "98-99"
    assert len(legend) == 50

    # score=0 and score=1 share bucket "0-1" -> same category.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]  # score=0 -> bucket "0-1"
    assert sample_id_to_colors[str(samples[1].sample_id)] == [3]  # score=1 -> bucket "0-1"
    assert sample_id_to_colors[str(samples[2].sample_id)] == [4]  # score=2 -> bucket "2-3"
    assert sample_id_to_colors[str(samples[99].sample_id)] == [52]  # score=99 -> bucket "98-99"


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

    # The legend is filter-aware: only values carried by a matching sample appear,
    # so "London" and "Berlin" (filtered out) are dropped and their samples report
    # no category. The survivors keep individual slots, ordered by label on the tie.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]  # Paris
    assert sample_id_to_colors[str(samples[1].sample_id)] == []  # London, hidden
    assert sample_id_to_colors[str(samples[2].sample_id)] == [4]  # Rome
    assert sample_id_to_colors[str(samples[3].sample_id)] == []  # Berlin, hidden

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {"3": "Paris", "4": "Rome"}


def test_get_embeddings2d__filter_promotes_metadata_value_out_of_other(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """A value buried in "Other" globally gets its own slot once filtered to."""
    n_samples = 300

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

    # More distinct values than fit in the 253 individual slots, one per sample.
    for i, sample in enumerate(samples):
        sample.sample["label"] = f"v{i:03d}"

    # Unfiltered: every value has frequency 1, so ordering is alphabetical and
    # the alphabetically-late values collapse into the trailing "Other" slot.
    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={"filters": {}, "color_by": {"type": "metadata_field", "key": "label"}},
    )
    assert response.status_code == 200
    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    legend_all = json.loads(table.schema.metadata[b"color_legend"])
    assert any(label.startswith("Other") for label in legend_all.values())
    assert "v299" not in legend_all.values()

    # Filter to the single sample whose value was inside "Other": it now is the
    # only value present, so it is promoted to its own individual slot.
    image_filter = ImageFilter(
        sample_filter=SampleFilter(sample_ids=[samples[299].sample_id]),
    )
    response = test_client.post(
        f"/api/collections/{collection_id}/embeddings2d/default",
        json={
            "filters": image_filter.model_dump(mode="json"),
            "color_by": {"type": "metadata_field", "key": "label"},
        },
    )
    assert response.status_code == 200
    table = ipc.open_stream(pa.BufferReader(response.content)).read_all()
    legend_filtered = json.loads(table.schema.metadata[b"color_legend"])
    assert legend_filtered == {"3": "v299"}


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
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]  # alpha
    assert sample_id_to_colors[str(samples[1].sample_id)] == [4]  # beta
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3, 4]  # both, sorted
    assert sample_id_to_colors[str(samples[3].sample_id)] == []  # untagged
    assert sample_id_to_colors[str(samples[4].sample_id)] == []  # untagged

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {
        "3": "alpha",
        "4": "beta",
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
    tag_hidden = tag_resolver.create(
        session=db_session,
        tag=TagCreate(collection_id=collection_id, name="hidden_tag", kind="sample"),
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
    # The hidden tag only lands on a filtered-out sample.
    tag_resolver.add_tag_to_sample(
        session=db_session, tag_id=tag_hidden.tag_id, sample=samples[2].sample
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
                "tag_ids": [str(tag_color.tag_id), str(tag_hidden.tag_id)],
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

    # All samples have the color tag → category 3. The hidden tag has no matching
    # sample, so it is dropped from the legend and contributes no category.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]
    assert sample_id_to_colors[str(samples[1].sample_id)] == [3]
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3]
    assert sample_id_to_colors[str(samples[3].sample_id)] == [3]

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {
        "3": "color_tag",
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
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]  # cat
    assert sample_id_to_colors[str(samples[1].sample_id)] == [4]  # dog
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3, 4]  # both, sorted
    assert sample_id_to_colors[str(samples[3].sample_id)] == []  # unannotated
    assert sample_id_to_colors[str(samples[4].sample_id)] == []  # unannotated

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {
        "3": "cat",
        "4": "dog",
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
    label_hidden = create_annotation_label(
        session=db_session, root_collection_id=collection_id, label_name="dog"
    )

    # All samples get annotated.
    for sample in samples:
        create_annotation(
            session=db_session,
            collection_id=collection_id,
            sample_id=sample.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
    # The hidden label only lands on a filtered-out sample.
    create_annotation(
        session=db_session,
        collection_id=collection_id,
        sample_id=samples[2].sample_id,
        annotation_label_id=label_hidden.annotation_label_id,
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
                "annotation_label_ids": [
                    str(label.annotation_label_id),
                    str(label_hidden.annotation_label_id),
                ],
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

    # All samples have "cat" → category 3. The hidden label has no matching
    # sample, so it is dropped from the legend and contributes no category.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(samples[0].sample_id)] == [3]
    assert sample_id_to_colors[str(samples[1].sample_id)] == [3]
    assert sample_id_to_colors[str(samples[2].sample_id)] == [3]
    assert sample_id_to_colors[str(samples[3].sample_id)] == [3]

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {"3": "cat"}


def test_get_embeddings2d__annotation_collection_color_by_own_label(
    test_client: TestClient,
    db_session: Session,
) -> None:
    """Annotation-collection samples are colored by the label they carry themselves.

    When the plotted collection is an annotation collection, each sample *is* an
    annotation rather than an image with child annotations, so coloring must read
    each annotation's own label.
    """
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    label_cat = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="cat"
    )
    label_dog = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="dog"
    )

    # Three "cat" annotations and two "dog" annotations, all on the same image.
    # Each annotation is its own sample in the annotation collection.
    annotation_labels = [
        label_cat,
        label_cat,
        label_cat,
        label_dog,
        label_dog,
    ]
    image = create_image(session=db_session, collection_id=collection.collection_id)
    embedding_model = create_embedding_model(
        session=db_session, collection_id=annotation_collection_id
    )
    annotations = []
    for i, label in enumerate(annotation_labels):
        annotation = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
        )
        create_sample_embedding(
            session=db_session,
            sample_id=annotation.sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=[float(i)] * EMBEDDING_DIMENSION,
        )
        annotations.append(annotation)

    response = test_client.post(
        f"/api/collections/{annotation_collection_id}/embeddings2d/default",
        json={
            "filters": {"filter_type": "annotations"},
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

    # "cat" is carried by 3 annotations and "dog" by 2, so "cat" ranks first and
    # takes category 3 while "dog" takes category 4.
    sample_id_to_colors = dict(zip(sample_ids_payload, color_categories))
    assert sample_id_to_colors[str(annotations[0].sample_id)] == [3]  # cat
    assert sample_id_to_colors[str(annotations[1].sample_id)] == [3]  # cat
    assert sample_id_to_colors[str(annotations[2].sample_id)] == [3]  # cat
    assert sample_id_to_colors[str(annotations[3].sample_id)] == [4]  # dog
    assert sample_id_to_colors[str(annotations[4].sample_id)] == [4]  # dog

    legend = json.loads(table.schema.metadata[b"color_legend"])
    assert legend == {
        "3": "cat",
        "4": "dog",
    }
