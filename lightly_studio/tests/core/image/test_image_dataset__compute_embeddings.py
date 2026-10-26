from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from PIL import Image
from sqlmodel import col, select

from lightly_studio import ImageDataset
from lightly_studio.embed import embedding_storage
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_embedding_model_resolver,
    collection_resolver,
)
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import (
    BoundingBoxCoordinates,
)
from tests.helpers_resolvers import create_annotation, create_annotation_label


def test_compute_embeddings__dataset_added_without_embedding(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg", "b.jpg"])
    sample_ids = _image_sample_ids(dataset=dataset)
    for sample_id in sample_ids:
        _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")
    _create_box(dataset=dataset, sample_id=sample_ids[0], source="predictions")

    dataset.compute_embeddings()

    source_names = {
        c.name
        for c in collection_resolver.get_annotation_collections(
            session=dataset.session, parent_collection_id=dataset.collection_id
        )
    }
    assert source_names == {"ground_truth", "predictions"}
    annotation_sample_ids = _annotation_sample_ids(dataset=dataset)
    assert len(annotation_sample_ids) == 3
    for sample_id in [*sample_ids, *annotation_sample_ids]:
        assert len(_vectors(dataset=dataset, sample_ids=[sample_id])) == 1


def test_compute_embeddings__embed_annotations_false(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg"])
    sample_id = _image_sample_ids(dataset=dataset)[0]
    _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")

    dataset.compute_embeddings(embed_annotations=False)

    assert len(_vectors(dataset=dataset, sample_ids=[sample_id])) == 1
    assert _vectors(dataset=dataset, sample_ids=_annotation_sample_ids(dataset=dataset)) == {}


def test_compute_embeddings__recompute_annotations(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg"])
    sample_id = _image_sample_ids(dataset=dataset)[0]
    _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")
    dataset.compute_embeddings()
    annotation_sample_id = _annotation_sample_ids(dataset=dataset)[0]
    annotation_collection = collection_resolver.get_annotation_collections(
        session=dataset.session, parent_collection_id=dataset.collection_id
    )[0]
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=dataset.session, collection_id=annotation_collection.collection_id
    )
    assert model_id is not None
    known_vector = (1.0, 2.0, 3.0)
    [crop] = annotation_resolver.get_annotation_crops_for_ids(
        session=dataset.session, annotation_sample_ids=[annotation_sample_id]
    )
    embedding_storage.store_embeddings(
        session=dataset.session,
        model_id=model_id,
        sample_ids=[annotation_sample_id],
        embeddings=np.array([known_vector], dtype=np.float32),
        source_fingerprints=[crop.source_fingerprint],
        show_progress=False,
        replace=True,
    )

    dataset.compute_embeddings()
    assert _vectors(dataset=dataset, sample_ids=[annotation_sample_id]) == {
        annotation_sample_id: known_vector
    }

    dataset.compute_embeddings(recompute_annotations=True)
    assert (
        _vectors(dataset=dataset, sample_ids=[annotation_sample_id])[annotation_sample_id]
        != known_vector
    )


def test_compute_embeddings__edited_box_gets_new_vector(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg", "b.jpg"])
    for sample_id in _image_sample_ids(dataset=dataset):
        _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")
    dataset.compute_embeddings()
    edited_id, untouched_id = _annotation_sample_ids(dataset=dataset)
    before = _vectors(dataset=dataset, sample_ids=[edited_id, untouched_id])
    annotation_resolver.update_bounding_box(
        session=dataset.session,
        annotation_id=edited_id,
        coordinates=BoundingBoxCoordinates(x=60, y=50, width=20, height=20),
    )

    dataset.compute_embeddings()

    after = _vectors(dataset=dataset, sample_ids=[edited_id, untouched_id])
    assert after[edited_id] != before[edited_id]
    assert after[untouched_id] == before[untouched_id]
    # The upsert stored the new fingerprint, so nothing is stale any more.
    annotation_collection = collection_resolver.get_annotation_collections(
        session=dataset.session, parent_collection_id=dataset.collection_id
    )[0]
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=dataset.session, collection_id=annotation_collection.collection_id
    )
    assert (
        annotation_resolver.get_unembedded_annotation_ids(
            session=dataset.session,
            annotation_collection_id=annotation_collection.collection_id,
            embedding_model_id=model_id,
        )
        == []
    )


def test_compute_embeddings__legacy_row_needs_recompute(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset = _create_dataset(tmp_path=tmp_path, image_names=["a.jpg"])
    sample_id = _image_sample_ids(dataset=dataset)[0]
    _create_box(dataset=dataset, sample_id=sample_id, source="ground_truth")
    dataset.compute_embeddings()
    annotation_sample_id = _annotation_sample_ids(dataset=dataset)[0]
    annotation_collection = collection_resolver.get_annotation_collections(
        session=dataset.session, parent_collection_id=dataset.collection_id
    )[0]
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=dataset.session, collection_id=annotation_collection.collection_id
    )
    assert model_id is not None
    known_vector = (1.0, 2.0, 3.0)
    row = dataset.session.get(SampleEmbeddingTable, (annotation_sample_id, model_id))
    assert row is not None
    row.embedding = np.array([known_vector], dtype=np.float32)[0]
    row.source_fingerprint = None
    dataset.session.add(row)
    dataset.session.commit()

    dataset.compute_embeddings()
    assert _vectors(dataset=dataset, sample_ids=[annotation_sample_id]) == {
        annotation_sample_id: known_vector
    }

    dataset.compute_embeddings(recompute_annotations=True)
    assert (
        _vectors(dataset=dataset, sample_ids=[annotation_sample_id])[annotation_sample_id]
        != known_vector
    )


def test_add_annotations__reembeds_edited_box(
    patch_collection: None,  # noqa: ARG001
    tmp_path: Path,
) -> None:
    dataset, images_path = _setup_dataset_with_images(
        tmp_path=tmp_path, file_names=["image1.jpg", "image2.jpg", "image3.jpg"]
    )
    first_json = tmp_path / "first.json"
    first_json.write_text(json.dumps(_coco_dict_with(file_names=["image1.jpg"])))
    dataset.add_annotations_from_coco(
        annotations_json=first_json,
        images_root=images_path,
        annotation_source="ground_truth",
    )
    [edited_id] = _annotation_sample_ids(dataset=dataset)
    other_json = tmp_path / "other.json"
    other_json.write_text(json.dumps(_coco_dict_with(file_names=["image2.jpg"])))
    dataset.add_annotations_from_coco(
        annotations_json=other_json,
        images_root=images_path,
        annotation_source="predictions",
    )
    [other_id] = set(_annotation_sample_ids(dataset=dataset)) - {edited_id}
    before = _vectors(dataset=dataset, sample_ids=[edited_id, other_id])
    annotation_resolver.update_bounding_box(
        session=dataset.session,
        annotation_id=edited_id,
        coordinates=BoundingBoxCoordinates(x=60, y=50, width=20, height=20),
    )
    second_json = tmp_path / "second.json"
    second_json.write_text(json.dumps(_coco_dict_with(file_names=["image3.jpg"])))

    dataset.add_annotations_from_coco(
        annotations_json=second_json,
        images_root=images_path,
        annotation_source="ground_truth",
    )

    after = _vectors(dataset=dataset, sample_ids=[edited_id, other_id])
    assert len(_annotation_sample_ids(dataset=dataset)) == 3
    assert after[edited_id] != before[edited_id]
    assert after[other_id] == before[other_id]


def _create_dataset(tmp_path: Path, image_names: list[str]) -> ImageDataset:
    for name in image_names:
        Image.new("RGB", (100, 100)).save(tmp_path / name)
    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_images_from_path(path=tmp_path, embed=False)
    return dataset


def _image_sample_ids(dataset: ImageDataset) -> list[UUID]:
    return [sample.sample_id for sample in dataset.query().to_list()]


def _create_box(dataset: ImageDataset, sample_id: UUID, source: str) -> None:
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id, label_name=uuid4().hex
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name=source,
    )


def _annotation_sample_ids(dataset: ImageDataset) -> list[UUID]:
    ids: list[UUID] = []
    for annotation_collection in collection_resolver.get_annotation_collections(
        session=dataset.session, parent_collection_id=dataset.collection_id
    ):
        ids.extend(
            annotation_resolver.get_croppable_annotation_ids(
                session=dataset.session,
                annotation_collection_id=annotation_collection.collection_id,
            )
        )
    return ids


def _vectors(dataset: ImageDataset, sample_ids: list[UUID]) -> dict[UUID, tuple[float, ...]]:
    dataset.session.expire_all()
    rows = dataset.session.exec(
        select(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id).in_(sample_ids))
    ).all()
    return {row.sample_id: tuple(float(v) for v in row.embedding) for row in rows}


def _coco_dict_with(file_names: list[str]) -> dict[str, Any]:
    return {
        "images": [
            {"id": i + 1, "file_name": name, "width": 100, "height": 100}
            for i, name in enumerate(file_names)
        ],
        "annotations": [
            {
                "id": i + 1,
                "image_id": i + 1,
                "category_id": 1,
                "bbox": [10, 10, 20, 20],
                "area": 400,
                "iscrowd": 0,
            }
            for i in range(len(file_names))
        ],
        "categories": [{"id": 1, "name": "cat"}],
    }


def _setup_dataset_with_images(tmp_path: Path, file_names: list[str]) -> tuple[ImageDataset, Path]:
    images_path = tmp_path / "images"
    images_path.mkdir()
    for name in file_names:
        Image.new("RGB", (100, 100)).save(images_path / name)
    dataset = ImageDataset.create(name="test_dataset")
    dataset.add_images_from_path(path=images_path, embed=False)
    return dataset, images_path
