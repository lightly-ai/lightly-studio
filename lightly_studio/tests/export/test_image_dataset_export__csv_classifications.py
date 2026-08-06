"""Tests for exporting image classifications to CSV."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query import ImageSampleField
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.export.image_dataset_export import ImageDatasetExport
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable
from tests.helpers_resolvers import (
    AnnotationDetails,
    ImageStub,
    create_annotation_label,
    create_annotations,
    create_collection,
    create_images,
)


def test_to_csv_classifications__exports_long_form_rows(
    db_session: Session, tmp_path: Path
) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path='/data/"quoted",image.jpg')],
    )
    cat = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name='cat, "tabby"',
    )
    indoor = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="indoor",
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[0].sample_id,
                annotation_label_id=cat.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
                confidence=0.949999988079071,
            ),
            AnnotationDetails(
                sample_id=images[0].sample_id,
                annotation_label_id=indoor.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=images[0].sample_id,
                annotation_label_id=indoor.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=images[0].sample_id,
                annotation_label_id=cat.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
        collection_name='model, "v1"',
    )

    output_csv = tmp_path / "classifications.csv"
    _exporter(session=db_session, collection=collection).to_csv_classifications(output_csv)

    rows = sorted(_read_rows(output_csv), key=lambda row: row["class_name"])
    assert rows == [
        {
            "file_path_abs": '/data/"quoted",image.jpg',
            "class_name": 'cat, "tabby"',
            "confidence": "0.949999988079071",
            "annotation_source": 'model, "v1"',
        },
        {
            "file_path_abs": '/data/"quoted",image.jpg',
            "class_name": "indoor",
            "confidence": "",
            "annotation_source": 'model, "v1"',
        },
        {
            "file_path_abs": '/data/"quoted",image.jpg',
            "class_name": "indoor",
            "confidence": "",
            "annotation_source": 'model, "v1"',
        },
    ]


def test_to_csv_classifications__filters_query_and_annotation_source(
    db_session: Session, tmp_path: Path
) -> None:
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="/data/small.jpg", height=100),
            ImageStub(path="/data/large.jpg", height=1000),
        ],
    )
    cat = create_annotation_label(
        session=db_session,
        root_collection_id=collection.collection_id,
        label_name="cat",
    )
    model_annotations = create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image.sample_id,
                annotation_label_id=cat.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
            for image in images
        ],
        collection_name="model",
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[0].sample_id,
                annotation_label_id=cat.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
        ],
        collection_name="ground_truth",
    )
    model_collection_id = model_annotations[0].annotation_collection_id
    all_sources_csv = tmp_path / "all_sources.csv"
    _exporter(session=db_session, collection=collection).to_csv_classifications(all_sources_csv)
    assert {row["annotation_source"] for row in _read_rows(all_sources_csv)} == {
        "ground_truth",
        "model",
    }

    query = DatasetQuery(dataset=collection, session=db_session).match(
        ImageSampleField.height < 500
    )

    output_csv = tmp_path / "filtered.csv"
    ImageDatasetExport(
        session=db_session,
        dataset_id=collection.dataset_id,
        samples=query,
    ).to_csv_classifications(
        output_csv=output_csv,
        annotation_collection_id=model_collection_id,
    )

    assert _read_rows(output_csv) == [
        {
            "file_path_abs": "/data/small.jpg",
            "class_name": "cat",
            "confidence": "",
            "annotation_source": "model",
        }
    ]


@pytest.mark.parametrize("as_string", [False, True])
def test_to_csv_classifications__writes_header_for_empty_export(
    db_session: Session, tmp_path: Path, as_string: bool
) -> None:
    collection = create_collection(session=db_session)
    create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/data/image.jpg")],
    )
    output_csv = tmp_path / "empty.csv"

    _exporter(session=db_session, collection=collection).to_csv_classifications(
        output_csv=str(output_csv) if as_string else output_csv
    )

    assert output_csv.read_text(encoding="utf-8") == (
        "file_path_abs,class_name,confidence,annotation_source\n"
    )


def test_to_csv_classifications__uses_default_output_path(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = create_collection(session=db_session)
    monkeypatch.chdir(tmp_path)

    _exporter(session=db_session, collection=collection).to_csv_classifications()

    assert (tmp_path / "classification_export.csv").exists()


def _exporter(session: Session, collection: CollectionTable) -> ImageDatasetExport:
    return ImageDatasetExport(
        session=session,
        dataset_id=collection.dataset_id,
        samples=DatasetQuery(dataset=collection, session=session),
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))
