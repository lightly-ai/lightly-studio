from __future__ import annotations

from pathlib import Path
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
    embedding_storage.store_embeddings(
        session=dataset.session,
        model_id=model_id,
        sample_ids=[annotation_sample_id],
        embeddings=np.array([known_vector], dtype=np.float32),
        source_fingerprints=["bbox1:0,0,1,1"],
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
