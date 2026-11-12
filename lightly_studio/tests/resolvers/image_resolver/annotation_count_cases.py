"""Shared data and filter cases for the image annotation count resolver tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
import sqlalchemy
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails, ImageStub

# The current count query has this text only when the annotations filter adds the parent IN.
PARENT_IN_MARKER = "DISTINCT annotation_base.parent_sample_id"


@dataclass
class CountData:
    """IDs of the data created by ``create_count_data``.

    Images 1, 2 and 3 have widths 100, 200 and 300.
    Source A: image 1 car, image 1 person, image 2 car, image 3 car classification.
    The other annotations are object detections.
    Source B: image 2 person, image 3 car.
    Image tag 1 is on image 1, image tag 2 is on images 2 and 3.
    The annotation tag is on the first source A annotation.
    """

    collection_id: UUID
    image_ids: list[UUID]
    source_a_id: UUID
    car_label_id: UUID
    image_tag_ids: list[UUID]
    annotation_tag_id: UUID
    source_a_annotation_ids: list[UUID]


def create_count_data(session: Session) -> CountData:
    """Create one image collection with two annotation sources."""
    collection_id = helpers_resolvers.create_collection(session=session).collection_id
    images = [
        helpers_resolvers.create_image(
            session=session,
            collection_id=collection_id,
            file_path_abs=f"/path/to/image_{width}.png",
            width=width,
        )
        for width in (100, 200, 300)
    ]
    car = helpers_resolvers.create_annotation_label(
        session=session, root_collection_id=collection_id, label_name="car"
    )
    person = helpers_resolvers.create_annotation_label(
        session=session, root_collection_id=collection_id, label_name="person"
    )
    source_a_annotations = helpers_resolvers.create_annotations(
        session=session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[0].sample_id, annotation_label_id=car.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=images[0].sample_id, annotation_label_id=person.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=images[1].sample_id, annotation_label_id=car.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=images[2].sample_id,
                annotation_label_id=car.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
        ],
        collection_name="source_a",
    )
    helpers_resolvers.create_annotations(
        session=session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=images[1].sample_id, annotation_label_id=person.annotation_label_id
            ),
            AnnotationDetails(
                sample_id=images[2].sample_id, annotation_label_id=car.annotation_label_id
            ),
        ],
        collection_name="source_b",
    )
    source_a_id = source_a_annotations[0].annotation_collection_id
    image_tags = [
        helpers_resolvers.create_tag(
            session=session, collection_id=collection_id, tag_name=f"image_tag_{i}"
        )
        for i in (1, 2)
    ]
    tag_resolver.add_sample_ids_to_tag_id(
        session=session, tag_id=image_tags[0].tag_id, sample_ids=[images[0].sample_id]
    )
    tag_resolver.add_sample_ids_to_tag_id(
        session=session,
        tag_id=image_tags[1].tag_id,
        sample_ids=[images[1].sample_id, images[2].sample_id],
    )
    annotation_tag = helpers_resolvers.create_tag(
        session=session, collection_id=source_a_id, tag_name="annotation_tag"
    )
    tag_resolver.add_tag_to_sample(
        session=session, tag_id=annotation_tag.tag_id, sample=source_a_annotations[0].sample
    )
    return CountData(
        collection_id=collection_id,
        image_ids=[image.sample_id for image in images],
        source_a_id=source_a_id,
        car_label_id=car.annotation_label_id,
        image_tag_ids=[tag.tag_id for tag in image_tags],
        annotation_tag_id=annotation_tag.tag_id,
        source_a_annotation_ids=[annotation.sample_id for annotation in source_a_annotations],
    )


def _on_sample_filter(annotations_filter: AnnotationsFilter) -> ImageFilter:
    return ImageFilter(sample_filter=SampleFilter(annotations_filter=annotations_filter))


# Each case is (group, build_filter). Source A is the selected source in each case. The groups:
# skip: the current count adds nothing to the total.
# strip: the annotations filter goes, other filters stay.
# keep: the annotations filter stays, with its parent IN.
CASES: list[Any] = [
    pytest.param("skip", lambda _: None, id="no_filter"),
    pytest.param("skip", lambda _: ImageFilter(), id="empty_image_filter"),
    pytest.param(
        "skip",
        lambda d: _on_sample_filter(
            annotations_filter=AnnotationsFilter(collection_ids=[d.source_a_id])
        ),
        id="sources_only",
    ),
    pytest.param(
        "skip",
        lambda _: _on_sample_filter(annotations_filter=AnnotationsFilter(collection_ids=[])),
        id="empty_source_list",
    ),
    pytest.param(
        "skip",
        lambda _: _on_sample_filter(annotations_filter=AnnotationsFilter()),
        id="empty_annotations_filter",
    ),
    pytest.param(
        "strip",
        lambda d: ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(collection_ids=[d.source_a_id]),
                tag_ids=[d.image_tag_ids[0]],
            )
        ),
        id="sources_and_image_tag",
    ),
    pytest.param(
        "strip",
        lambda d: ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(collection_ids=[d.source_a_id])
            ),
            width=FilterDimensions(min=150),
        ),
        id="sources_and_width",
    ),
    pytest.param(
        "strip",
        lambda d: ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(collection_ids=[d.source_a_id]),
                region_sample_ids=[d.image_ids[0]],
            )
        ),
        id="sources_and_image_region",
    ),
    pytest.param(
        "keep",
        lambda d: _on_sample_filter(
            annotations_filter=AnnotationsFilter(
                collection_ids=[d.source_a_id], annotation_label_ids=[d.car_label_id]
            )
        ),
        id="sources_and_label",
    ),
    pytest.param(
        "keep",
        lambda d: _on_sample_filter(
            annotations_filter=AnnotationsFilter(
                collection_ids=[d.source_a_id],
                annotation_types=[AnnotationType.OBJECT_DETECTION],
            )
        ),
        id="sources_and_type",
    ),
    pytest.param(
        "keep",
        lambda d: _on_sample_filter(
            annotations_filter=AnnotationsFilter(
                collection_ids=[d.source_a_id], tag_ids=[d.annotation_tag_id]
            )
        ),
        id="sources_and_annotation_tag",
    ),
    pytest.param(
        "keep",
        lambda d: _on_sample_filter(
            annotations_filter=AnnotationsFilter(
                collection_ids=[d.source_a_id], sample_ids=[d.source_a_annotation_ids[0]]
            )
        ),
        id="sources_and_annotation_ids",
    ),
    pytest.param(
        "keep",
        lambda d: _on_sample_filter(
            annotations_filter=AnnotationsFilter(
                collection_ids=[d.source_a_id], region_sample_ids=[]
            )
        ),
        id="sources_and_empty_annotation_region",
    ),
    pytest.param(
        "keep",
        lambda d: _on_sample_filter(
            annotations_filter=AnnotationsFilter(
                collection_ids=[d.source_a_id], region_sample_ids=[d.source_a_annotation_ids[0]]
            )
        ),
        id="sources_and_annotation_region",
    ),
]

# The same cases without their group, for tests that check counts only.
BUILD_FILTERS: list[Any] = [pytest.param(case.values[1], id=case.id) for case in CASES]

BuildFilter = Callable[[CountData], "ImageFilter | None"]


def create_images_in_plot(
    session: Session, coordinates: list[tuple[float, float]]
) -> tuple[UUID, list[ImageTable]]:
    """Create one embedded image per entry of ``coordinates`` in a saved 2D plot."""
    collection_id = helpers_resolvers.create_collection(session=session).collection_id
    embedding_model = helpers_resolvers.create_embedding_model(
        session=session,
        collection_id=collection_id,
        embedding_dimension=3,
        set_as_default=True,
    )
    images = helpers_resolvers.create_samples_with_embeddings(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path=f"sample_{i}.png"), [float(i) + 0.1, 0.2, 0.3])
            for i in range(len(coordinates))
        ],
    )
    helpers_resolvers.create_saved_plot(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        coordinates={image.sample_id: point for image, point in zip(images, coordinates)},
    )
    return collection_id, images


@contextmanager
def record_statements(session: Session) -> Iterator[list[str]]:
    """Collect the SQL text of each statement that the session executes."""
    statements: list[str] = []

    def listener(_conn: Any, _cursor: Any, statement: str, *_: Any) -> None:
        statements.append(statement)

    engine = session.get_bind()
    sqlalchemy.event.listen(engine, "before_cursor_execute", listener)
    try:
        yield statements
    finally:
        sqlalchemy.event.remove(engine, "before_cursor_execute", listener)
