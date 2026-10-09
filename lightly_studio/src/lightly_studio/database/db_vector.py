"""Dialect-aware vector types and functions.

Embeddings are stored as pgvector's VECTOR() on PostgreSQL and ARRAY(Float) on DuckDB,
and returned to Python as ``float32`` numpy arrays (~4 B vs ~50 B per element for a
Python float in a list), which bounds memory when loading many of them.
"""

from __future__ import annotations

from typing import Annotated, Any

import numpy as np
from numpy.typing import NDArray
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from sqlalchemy import ARRAY, Float
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import TypeDecorator, TypeEngine
from sqlmodel import Session
from typing_extensions import TypeAlias

# A single embedding vector. Always 1-D float32 numpy; a batch is a Sequence[Embedding].
Embedding: TypeAlias = NDArray[np.float32]


class VectorType(TypeDecorator[Embedding]):
    """A dialect-aware vector column with a float32 numpy Python representation.

    Returns pgvector's VECTOR() for PostgreSQL and ARRAY(Float) for DuckDB.
    """

    impl = ARRAY(Float)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Return the dialect-specific type for the vector column.

        Returns pgvector VECTOR for PostgreSQL and ARRAY(Float) for DuckDB.
        Raises NotImplementedError for unsupported dialects.
        """
        if dialect.name == "postgresql":
            # Keep this import local because pgvector is only needed for PostgreSQL.
            from pgvector.sqlalchemy import Vector  # noqa: PLC0415

            return dialect.type_descriptor(Vector())
        if dialect.name == "duckdb":
            return dialect.type_descriptor(ARRAY(Float))
        raise NotImplementedError(
            f"Unsupported dialect: {dialect.name}. Only 'postgresql' and 'duckdb' are supported."
        )

    def process_result_value(
        self,
        value: Any,
        dialect: Dialect,  # noqa: ARG002
    ) -> Embedding | None:
        """Return the stored array as a float32 numpy array."""
        return None if value is None else np.asarray(value, dtype=np.float32)


def _validate_embedding(value: Any) -> Embedding:
    """Coerce to a 1-D float32 array, enforcing the single-vector Embedding contract."""
    array = np.asarray(value, dtype=np.float32)
    if array.ndim != 1:
        raise ValueError(f"Embedding must be a 1-D vector, got {array.ndim}-D.")
    return array


class _NumpyArrayPydanticAnnotation:
    """Pydantic core schema that lets a model field be typed as a numpy ``Embedding``.

    Pydantic v2 has no built-in support for ``np.ndarray``, so a model that declares
    ``embedding: NumpyArray`` (e.g. ``SampleEmbeddingCreate``) needs this to validate
    input into a 1-D float32 array and serialize it back to a list, without resorting
    to ``arbitrary_types_allowed``.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            _validate_embedding,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda value: value.tolist()
            ),
        )


# Numpy field type for pydantic models (validates + serializes, no arbitrary_types_allowed).
NumpyArray = Annotated[Embedding, _NumpyArrayPydanticAnnotation]


class cosine_distance(GenericFunction[float]):  # noqa: N801
    """Cosine distance function that compiles to dialect-specific SQL.

    Uses the <=> operator on both DuckDB and PostgreSQL (pgvector).
    PostgreSQL requires explicit ::vector casts on both operands.
    """

    type = Float()
    inherit_cache = True


@compiles(cosine_distance)
def _compile_cosine_distance_unsupported(
    element: cosine_distance, compiler: SQLCompiler, **kw: Any
) -> str:
    """Raise for unsupported dialects."""
    raise NotImplementedError(
        f"Unsupported dialect: {compiler.dialect.name}."
        " Only 'postgresql' and 'duckdb' are supported."
    )


@compiles(cosine_distance, "duckdb")
def _compile_cosine_distance_duckdb(
    element: cosine_distance, compiler: SQLCompiler, **kw: Any
) -> str:
    """DuckDB compilation: uses <=> without cast."""
    left, right = list(element.clauses)
    return f"({compiler.process(left, **kw)} <=> {compiler.process(right, **kw)})"


@compiles(cosine_distance, "postgresql")
def _compile_cosine_distance_postgresql(
    element: cosine_distance, compiler: SQLCompiler, **kw: Any
) -> str:
    """PostgreSQL compilation: uses <=> with ::vector cast on both operands."""
    left, right = list(element.clauses)
    return f"({compiler.process(left, **kw)}::vector <=> {compiler.process(right, **kw)}::vector)"


class vector_element(GenericFunction[float]):  # noqa: N801
    """Extract a single element from a vector column by 1-based index.

    Compiles to dialect-specific SQL:
    - DuckDB: ``col[index]``
    - PostgreSQL: ``(col::real[])[index]`` (pgvector vectors need a cast first)
    """

    type = Float()
    inherit_cache = True


@compiles(vector_element)
def _compile_vector_element_unsupported(
    element: vector_element, compiler: SQLCompiler, **kw: Any
) -> str:
    """Raise for unsupported dialects."""
    raise NotImplementedError(
        f"Unsupported dialect: {compiler.dialect.name}."
        " Only 'postgresql' and 'duckdb' are supported."
    )


@compiles(vector_element, "duckdb")
def _compile_vector_element_duckdb(
    element: vector_element, compiler: SQLCompiler, **kw: Any
) -> str:
    """DuckDB compilation: col[index]."""
    col, index = list(element.clauses)
    return f"{compiler.process(col, **kw)}[{compiler.process(index, **kw)}]"


@compiles(vector_element, "postgresql")
def _compile_vector_element_postgresql(
    element: vector_element, compiler: SQLCompiler, **kw: Any
) -> str:
    """PostgreSQL compilation: (col::real[])[index]."""
    col, index = list(element.clauses)
    return f"({compiler.process(col, **kw)}::real[])[{compiler.process(index, **kw)}]"


class inner_product(GenericFunction[float]):  # noqa: N801
    """Inner (dot) product of two vectors that compiles to dialect-specific SQL.

    - DuckDB: ``list_inner_product(a, b)`` without casts
    - PostgreSQL: pgvector's ``inner_product(a::vector, b::vector)``
    """

    type = Float()
    inherit_cache = True


@compiles(inner_product)
def _compile_inner_product_unsupported(
    element: inner_product, compiler: SQLCompiler, **kw: Any
) -> str:
    """Raise for unsupported dialects."""
    raise NotImplementedError(
        f"Unsupported dialect: {compiler.dialect.name}."
        " Only 'postgresql' and 'duckdb' are supported."
    )


@compiles(inner_product, "duckdb")
def _compile_inner_product_duckdb(element: inner_product, compiler: SQLCompiler, **kw: Any) -> str:
    """DuckDB compilation: list_inner_product without cast."""
    left, right = list(element.clauses)
    return f"list_inner_product({compiler.process(left, **kw)}, {compiler.process(right, **kw)})"


@compiles(inner_product, "postgresql")
def _compile_inner_product_postgresql(
    element: inner_product, compiler: SQLCompiler, **kw: Any
) -> str:
    """PostgreSQL compilation: pgvector's inner_product with ::vector casts."""
    left, right = list(element.clauses)
    left_sql = compiler.process(left, **kw)
    right_sql = compiler.process(right, **kw)
    return f"inner_product({left_sql}::vector, {right_sql}::vector)"


class loaded_vector(GenericFunction[Embedding]):  # noqa: N801
    """A vector column that the database loads once for each row.

    PostgreSQL stores vectors over about 2 KB out of line (TOAST). Each use of such a column
    in an expression loads the vector again. Select this function in a subquery with
    ``OFFSET 0`` and use the subquery column, so that each vector loads only once.

    Compiles to dialect-specific SQL:
    - DuckDB: ``col`` (DuckDB has no TOAST)
    - PostgreSQL: ``subvector(col, 1, dimension)``, an in-memory copy of the vector
    """

    type = VectorType()
    inherit_cache = True


@compiles(loaded_vector)
def _compile_loaded_vector_unsupported(
    element: loaded_vector, compiler: SQLCompiler, **kw: Any
) -> str:
    """Raise for unsupported dialects."""
    raise NotImplementedError(
        f"Unsupported dialect: {compiler.dialect.name}."
        " Only 'postgresql' and 'duckdb' are supported."
    )


@compiles(loaded_vector, "duckdb")
def _compile_loaded_vector_duckdb(element: loaded_vector, compiler: SQLCompiler, **kw: Any) -> str:
    """DuckDB compilation: col."""
    col, _dimension = list(element.clauses)
    return compiler.process(col, **kw)


@compiles(loaded_vector, "postgresql")
def _compile_loaded_vector_postgresql(
    element: loaded_vector, compiler: SQLCompiler, **kw: Any
) -> str:
    """PostgreSQL compilation: subvector(col, 1, dimension)."""
    col, dimension = list(element.clauses)
    return f"subvector({compiler.process(col, **kw)}, 1, {compiler.process(dimension, **kw)})"


def get_pgvector_connection(session: Session) -> Any:
    """Return the session's psycopg connection with pgvector registered.

    Registers pgvector once per connection (cached in ``connection.info``) so ``vector``
    columns are decoded from their binary wire format via ``np.frombuffer`` instead of
    parsed from text. PostgreSQL-only; the returned object is the raw DBAPI connection,
    intended for reads that bypass SQLAlchemy's result handling.
    """
    connection = session.connection().connection
    driver_connection = connection.driver_connection
    if driver_connection is None:  # pragma: no cover - a live session always has one
        raise RuntimeError("PostgreSQL session has no underlying psycopg connection.")
    if not connection.info.get("pgvector_registered"):
        # pgvector is only needed for PostgreSQL, so import it locally.
        from pgvector.psycopg import register_vector  # noqa: PLC0415

        register_vector(driver_connection)
        connection.info["pgvector_registered"] = True
    return driver_connection
