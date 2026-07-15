"""Configuration of the tests."""

from __future__ import annotations

import contextlib
from collections.abc import Generator, Sequence
from typing import Any
from uuid import UUID

import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_mock import MockerFixture
from sqlmodel import Session, SQLModel
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from lightly_studio.api import features
from lightly_studio.api.app import app
from lightly_studio.database import db_manager
from lightly_studio.database.db_manager import DatabaseBackend, DatabaseEngine
from lightly_studio.dataset import embedding_manager
from lightly_studio.dataset.embedding_generator import RandomEmbeddingGenerator
from lightly_studio.dataset.embedding_manager import EmbeddingManager, EmbeddingManagerProvider
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
)
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.models.image import ImageTable
from lightly_studio.models.tag import TagCreate, TagTable
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    tag_resolver,
)
from tests.helpers_resolvers import (
    ImageStub,
    create_images,
)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --postgres CLI option to run tests against a real Postgres container."""
    parser.addoption(
        "--postgres",
        action="store_true",
        default=False,
        help="Run tests against a Postgres container instead of file-based DuckDB.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip postgres_only tests unless the suite runs with --postgres.

    The ``postgres_only`` marker is registered in ``pytest.ini``.
    """
    if config.getoption("--postgres"):
        return
    skip_marker = pytest.mark.skip(reason="postgres_only: skipped under DuckDB")
    for item in items:
        if "postgres_only" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def _use_postgres(request: pytest.FixtureRequest) -> bool:
    """Return True when the test suite is running against Postgres."""
    return bool(request.config.getoption("--postgres"))


@pytest.fixture(scope="session")
def postgres_url(_use_postgres: bool) -> Generator[str | None, None, None]:
    """Start a Postgres container and yield its URL, or None for DuckDB."""
    if not _use_postgres:
        yield None
        return

    pg_container = PostgresContainer(
        image="pgvector/pgvector:0.8.1-pg18-bookworm", driver="psycopg"
    )
    pg_container.start()
    yield pg_container.get_connection_url()
    pg_container.stop()


@pytest.fixture(scope="session")
def _postgres_engine(postgres_url: str | None) -> Generator[DatabaseEngine | None, None, None]:
    """Create a session-scoped DatabaseEngine for Postgres, or None for DuckDB."""
    if postgres_url is None:
        yield None
        return

    engine = DatabaseEngine(engine_url=postgres_url, single_threaded=True)
    yield engine
    engine.close()


@pytest.fixture(scope="session")
def _duckdb_engine(
    _use_postgres: bool,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[DatabaseEngine | None, None, None]:
    """Create a session-scoped on-disk DuckDB engine, or None under --postgres.

    Each pytest-xdist worker is its own process, so this yields one DuckDB
    database per worker, building the schema once per worker instead of per test.

    A file is used instead of ``:memory:`` on purpose: a reused in-memory
    connection serves a stale cached query plan after many DELETE/INSERT cycles
    (our per-test reset), making parameterized ``LIMIT``/``OFFSET`` reads return
    zero rows. The file backend invalidates these plans and matches production.
    """
    if _use_postgres:
        yield None
        return

    db_path = tmp_path_factory.mktemp("duckdb") / "test.duckdb"
    engine = DatabaseEngine(engine_url=f"duckdb:///{db_path}", single_threaded=True)
    yield engine
    engine.close()


@pytest.fixture
def _db_engine(
    _use_postgres: bool,
    _postgres_engine: DatabaseEngine | None,
    _duckdb_engine: DatabaseEngine | None,
) -> Generator[DatabaseEngine, None, None]:
    """Provide the per-worker DatabaseEngine for each test.

    Reuses one session-scoped engine (file-based DuckDB by default, or Postgres
    under --postgres). Resets data between tests keeping the DB schema.
    That saves the schema creation time across 1000s of tests, speeding up our CI.
    """
    engine = _postgres_engine if _use_postgres else _duckdb_engine
    assert engine is not None
    yield engine
    with engine.session() as session:
        session.rollback()
        _truncate_tables(session, backend=engine.backend)


@pytest.fixture
def db_session(
    _db_engine: DatabaseEngine,
) -> Generator[Session, None, None]:
    """Create a test database manager session."""
    with _db_engine.session() as session:
        yield session


@pytest.fixture
def test_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client for API requests."""
    client = TestClient(app)

    def get_session_override() -> Session:
        return db_session

    app.dependency_overrides[db_manager._session_dependency] = get_session_override

    yield client

    app.dependency_overrides.clear()


@pytest.fixture
def media_test_client(
    db_session: Session,
    mocker: MockerFixture,
) -> TestClient:
    """Test client for media routes that open their own DB session.

    Media endpoints call ``db_manager.session()`` directly instead of using the
    session dependency. Patch it to yield the per-test ``db_session`` so requests
    read the data the test creates: the DuckDB ``StaticPool`` has a single
    connection, which cannot host two concurrent sessions.
    """

    @contextlib.contextmanager
    def session_override() -> Generator[Session, None, None]:
        yield db_session

    mocker.patch.object(db_manager, "session", session_override)
    return TestClient(app)


@pytest.fixture
def collection(db_session: Session) -> CollectionTable:
    """Create a test collection."""
    collection_input = CollectionCreate(name="test_collection", sample_type=SampleType.IMAGE)
    return collection_resolver.create(db_session, collection_input)


@pytest.fixture
def collection_id(collections: list[CollectionTable]) -> UUID:
    """Return the ID of the first collection."""
    return collections[0].collection_id


@pytest.fixture
def collections(db_session: Session) -> list[CollectionTable]:
    """Create multiple test collections."""
    collections = []
    for i in range(10):
        collection_input = CollectionCreate(
            name=f"test_collection_{i}", sample_type=SampleType.IMAGE
        )
        collection = collection_resolver.create(db_session, collection_input)
        collections.append(collection)
    return collections


@pytest.fixture
def embedding_model_input(collection: CollectionTable) -> EmbeddingModelCreate:
    """Create an EmbeddingModelCreate instance."""
    return EmbeddingModelCreate(
        collection_id=collection.collection_id,
        embedding_dimension=3,
        name="test_model",
    )


@pytest.fixture
def samples(db_session: Session, collection: CollectionTable) -> list[ImageTable]:
    """Create test samples."""
    return create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[
            ImageStub(
                path=f"/test/path/test_image_{i}.jpg",
                width=640,
                height=480,
            )
            for i in range(10)
        ],
    )


@pytest.fixture
def annotation_labels(
    db_session: Session, collections: list[CollectionTable]
) -> list[AnnotationLabelTable]:
    """Create multiple test annotation labels."""
    dataset_id = collections[0].dataset_id
    labels = []
    for i in range(5):
        label_input = AnnotationLabelCreate(
            annotation_label_name=f"test_label_{i}",
            dataset_id=dataset_id,
        )
        label = annotation_label_resolver.create(db_session, label_input)
        labels.append(label)
    return labels


class AnnotationsTestData(BaseModel):
    """Test data for annotations."""

    tags: list[TagTable]
    annotation_labels: list[AnnotationLabelTable]
    collections: list[CollectionTable]
    annotations: Sequence[AnnotationBaseTable]
    samples: list[ImageTable]

    labeled_annotations: dict[UUID, list[AnnotationBaseTable]] = {}


def create_test_base_annotation(
    db_session: Session,
    samples: list[ImageTable],
    annotation_label: AnnotationLabelTable,
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
) -> AnnotationBaseTable:
    """Create a test object detection annotation input."""
    annotation_base_input = AnnotationCreate(
        parent_sample_id=samples[0].sample_id,
        annotation_type=annotation_type,
        annotation_label_id=annotation_label.annotation_label_id,
        confidence=0.95,
    )

    annotation_ids = annotation_resolver.create_many(
        db_session,
        parent_collection_id=samples[0].sample.collection_id,
        annotations=[annotation_base_input],
    )

    assert len(annotation_ids) == 1
    annotation = annotation_resolver.get_by_id(db_session, annotation_ids[0])
    assert annotation is not None, "Failed to retrieve the created annotation."
    return annotation


def create_test_base_annotations(
    db_session: Session,
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
) -> list[AnnotationBaseTable]:
    """Create multiple test object detection annotations."""
    annotation_base_inputs = [
        AnnotationCreate(
            parent_sample_id=sample.sample_id,
            annotation_label_id=annotation_labels[i % 2].annotation_label_id,
            annotation_type=annotation_type,
            confidence=0.9 - (i * 0.1),
        )
        for i, sample in enumerate(samples[:3])
    ]
    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=samples[0].sample.collection_id,
        annotations=annotation_base_inputs,
    )
    assert len(annotation_ids) == len(annotation_base_inputs)
    return list(annotation_resolver.get_by_ids(session=db_session, annotation_ids=annotation_ids))


@pytest.fixture
def annotation_tags(
    db_session: Session,
    collections: list[CollectionTable],
) -> list[TagTable]:
    """Create a list of annotation labels for testing."""
    tags = []
    for i in range(4):
        tag = tag_resolver.create(
            db_session,
            TagCreate(
                collection_id=collections[i % 2].collection_id,
                name=f"Test Tag {i}",
                kind="annotation",
            ),
        )
        tags.append(tag)
    return tags


@pytest.fixture
def sample_tags(
    db_session: Session,
    collections: list[CollectionTable],
) -> list[TagTable]:
    """Create a list of sample tags for testing."""
    tags = []
    for i in range(4):
        tag = tag_resolver.create(
            db_session,
            TagCreate(
                collection_id=collections[i % 2].collection_id,
                name=f"Test Sample Tag {i}",
                kind="sample",
            ),
        )
        tags.append(tag)
    return tags


@pytest.fixture
def samples_assigned_with_tags(
    db_session: Session,
    samples: list[ImageTable],
    sample_tags: list[TagTable],
) -> tuple[list[ImageTable], list[TagTable]]:
    """Create a list of sample tags for testing."""
    assert len(samples) >= 2, "At least 2 samples are required for this fixture."
    assert len(sample_tags) >= 2, "At least 2 sample tags are required for this fixture."
    tag_resolver.add_tag_to_sample(
        session=db_session,
        tag_id=sample_tags[0].tag_id,
        sample=samples[0].sample,
    )
    tag_resolver.add_tag_to_sample(
        session=db_session,
        tag_id=sample_tags[1].tag_id,
        sample=samples[1].sample,
    )
    return samples[:2], sample_tags[:2]


@pytest.fixture
def annotations_test_data(
    db_session: Session,
    collections: list[CollectionTable],
    samples: list[ImageTable],
    annotation_labels: list[AnnotationLabelTable],
    samples_assigned_with_tags: tuple[list[ImageTable], list[TagTable]],
) -> AnnotationsTestData:
    """Create test data in test database."""
    annotation_types: list[AnnotationType] = [
        AnnotationType.CLASSIFICATION,
        AnnotationType.OBJECT_DETECTION,
        AnnotationType.SEGMENTATION_MASK,
    ]

    annotations_to_create_first_collection: list[AnnotationCreate] = []
    annotations_to_create_second_collection: list[AnnotationCreate] = []

    # Create annotation for every annotation type.
    for annotation_type in annotation_types:
        # Create 3 annotations for each type
        for i in range(3):
            # We distribute annotation labels across the annotations
            # to ensure that we have different labels for each annotation.
            if len(annotation_labels) < 2:
                raise ValueError("At least 2 annotation labels are required.")
            label_id = annotation_labels[i % 2].annotation_label_id

            annotation = AnnotationCreate(
                annotation_label_id=label_id,
                confidence=0.9 - (i * 0.1),
                parent_sample_id=samples[i % 2].sample_id,
                annotation_type=annotation_type,
            )
            if annotation_type == AnnotationType.OBJECT_DETECTION:
                annotation.x = 10
                annotation.y = 20
                annotation.width = 100
                annotation.height = 200
            elif annotation_type == AnnotationType.SEGMENTATION_MASK:
                annotation.x = 15
                annotation.y = 25
                annotation.width = 150
                annotation.height = 250
                annotation.segmentation_mask = [1, 2, 3, 4]
            elif annotation_type == AnnotationType.CLASSIFICATION:
                # Classification annotations carry an optional temporal span.
                annotation.start_time_s = 1.5
                annotation.end_time_s = 4.0
            if i % 2 == 0:
                annotations_to_create_first_collection.append(annotation)
            else:
                annotations_to_create_second_collection.append(annotation)

    annotation_ids = annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collections[0].collection_id,
        annotations=annotations_to_create_first_collection,
    )
    annotation_ids += annotation_resolver.create_many(
        session=db_session,
        parent_collection_id=collections[1].collection_id,
        annotations=annotations_to_create_second_collection,
    )
    annotations = annotation_resolver.get_by_ids(db_session, annotation_ids)
    labeled_annotations: dict[UUID, list[AnnotationBaseTable]] = {}

    for _annotation in annotations:
        if _annotation.annotation_label_id not in labeled_annotations:
            labeled_annotations[_annotation.annotation_label_id] = []

        labeled_annotations[_annotation.annotation_label_id].append(_annotation)

    return AnnotationsTestData(
        labeled_annotations=labeled_annotations,
        annotations=annotations,
        tags=samples_assigned_with_tags[1],
        annotation_labels=annotation_labels,
        collections=collections,
        samples=samples,
    )


@pytest.fixture
def annotation_tags_assigned(
    db_session: Session,
    collections: list[CollectionTable],
    annotations_test_data: list[AnnotationBaseTable],  # noqa: ARG001
) -> list[TagTable]:
    """Create a list of annotation labels for testing."""
    annotations_all = annotation_resolver.get_all(
        db_session,
    ).annotations

    tags = tag_resolver.get_all_by_collection_id(
        db_session, collection_id=collections[0].collection_id
    )

    # assign the first tag to the 2 annotations
    for i in range(2):
        tag_resolver.add_tag_to_sample(
            session=db_session,
            tag_id=tags[0].tag_id,
            sample=annotations_all[i].sample,
        )

    # assign the second tag to the 3 annotations
    for i in range(2, 5):
        tag_resolver.add_tag_to_sample(
            session=db_session,
            tag_id=tags[1].tag_id,
            sample=annotations_all[i].sample,
        )

    return tags


def assert_contains_properties(
    obj: Any,
    expected_props: BaseModel | dict[str, Any],
    float_tolerance: float = 0.01,
) -> None:
    """Assert that obj contains all properties from expected_props."""
    if hasattr(expected_props, "model_dump"):
        expected_dict = expected_props.model_dump()
    else:
        expected_dict = expected_props

    for key, expected_value in expected_dict.items():
        assert hasattr(obj, key), f"Object missing property: {key}"
        actual_value = getattr(obj, key)

        if isinstance(expected_value, float):
            assert actual_value == pytest.approx(expected_value, abs=float_tolerance)
        else:
            assert actual_value == expected_value


@pytest.fixture
def patch_collection(
    mocker: MockerFixture,
    _db_engine: DatabaseEngine,
) -> None:
    """Fixture to patch the collection resources.

    Patches get_engine() to return the per-test engine (file-based DuckDB or
    session-scoped Postgres). Table truncation is handled by _db_engine teardown.
    """
    # Create a mock database manager.
    mocker.patch.object(
        db_manager,
        "get_engine",
        return_value=_db_engine,
    )

    # Create a test-specific EmbeddingManager singleton.
    mocker.patch.object(
        EmbeddingManagerProvider,
        "get_embedding_manager",
        return_value=EmbeddingManager(),
    )

    # Fake the default embedding generator.
    mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=RandomEmbeddingGenerator(),
    )

    # Create test-specific lightly_studio_active_features.
    mocker.patch.object(features, "lightly_studio_active_features", [])


def _truncate_tables(session: Session, backend: DatabaseBackend) -> None:
    """Reset all tables in the database to clear state between tests."""
    if backend == DatabaseBackend.POSTGRESQL:
        _truncate_tables_postgres(session)
    else:
        _truncate_tables_duckdb(session)


def _truncate_tables_postgres(session: Session) -> None:
    """Reset all tables on Postgres with TRUNCATE ... CASCADE."""
    for table in reversed(SQLModel.metadata.sorted_tables):
        session.execute(sqlalchemy.text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
    session.commit()


def _truncate_tables_duckdb(session: Session) -> None:
    """Reset all tables on DuckDB with ordered DELETEs.

    DuckDB has no TRUNCATE ... CASCADE and validates FK constraints against
    committed state, so it deletes child-first and commits after each table.
    Self-referential tables need special handling (see the helper).
    """
    for table in reversed(SQLModel.metadata.sorted_tables):
        if any(fk.column.table is table for fk in table.foreign_keys):
            _delete_self_referential_table(session, table)
        else:
            session.execute(sqlalchemy.text(f'DELETE FROM "{table.name}"'))
            session.commit()


def _delete_self_referential_table(session: Session, table: sqlalchemy.Table) -> None:
    """Empty a self-referential table by repeatedly deleting its leaf rows.

    DuckDB can't delete a self-referential table in one statement (strict FK checks),
    and treats UPDATE as delete+insert, so even nulling the FK column does not work.
    We delete the unreferenced rows round by round until the table is empty.
    """
    (pk_column,) = table.primary_key.columns
    self_ref_columns = [fk.parent.name for fk in table.foreign_keys if fk.column.table is table]
    parent_keys = ", ".join(f'"{column}"' for column in self_ref_columns)
    not_null = " OR ".join(f'"{column}" IS NOT NULL' for column in self_ref_columns)
    delete_leaves = (
        f'DELETE FROM "{table.name}" WHERE "{pk_column.name}" NOT IN '
        f'(SELECT {parent_keys} FROM "{table.name}" WHERE {not_null})'
    )
    count_rows = f'SELECT COUNT(*) FROM "{table.name}"'
    # DuckDB reports rowcount as -1, so condition on COUNT(*) instead.
    remaining = session.execute(sqlalchemy.text(count_rows)).scalar_one()
    while remaining > 0:
        session.execute(sqlalchemy.text(delete_leaves))
        session.commit()
        # Check that the number of rows is decreasing.
        previous, remaining = remaining, session.execute(sqlalchemy.text(count_rows)).scalar_one()
        assert remaining < previous, f'"{table.name}" did not shrink; possible FK cycle'
