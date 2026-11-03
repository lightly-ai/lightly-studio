"""Rebuild every table of a LightlyStudio DuckDB file, so that all its indexes are rebuilt.

DuckDB can save an index without rows that it replayed from the WAL (duckdb/duckdb#26106).
A delete of such a row then fails with "Failed to delete all rows from index" and
invalidates the database. A dropped and recreated table gets new, complete indexes.

    python repair_duckdb_indexes.py --db ~/data/caltech-ux-run-dbs/demo.db

Stop the server that uses the file first. The script copies the file to
<file>.bak-<timestamp> before it changes anything.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import duckdb


def main() -> None:
    """Back up the file, rebuild all tables and print the row counts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    db = args.db.expanduser()

    backup = _backup(db=db)
    print(f"Backup: {backup}")

    # Same storage version as the app, see db_manager.DatabaseEngine.
    con = duckdb.connect(str(db), config={"storage_compatibility_version": "v1.0.0"})
    # Write the replayed WAL into the file before the next checkpoint can lose index rows.
    con.execute("CHECKPOINT")

    tables = _tables_parents_first(con=con)
    counts_before = {table: _count(con=con, table=table) for table in tables}
    _rebuild(con=con, tables=tables)
    con.execute("CHECKPOINT")

    for table in tables:
        after = _count(con=con, table=table)
        flag = "" if after == counts_before[table] else "  <-- MISMATCH"
        print(f"{table:40} {counts_before[table]:>8} -> {after:>8}{flag}")
    con.close()


def _backup(db: Path) -> Path:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup = db.with_name(f"{db.name}.bak-{stamp}")
    shutil.copy2(db, backup)
    wal = db.with_name(f"{db.name}.wal")
    if wal.exists():
        shutil.copy2(wal, backup.with_name(f"{backup.name}.wal"))
    return backup


def _rebuild(con: duckdb.DuckDBPyConnection, tables: list[str]) -> None:
    """Copy all tables to temp tables, drop them, recreate them and insert the rows again."""
    create_sql = {table: _create_table_sql(con=con, table=table) for table in tables}
    index_sql = {
        table: [
            sql
            for (sql,) in con.execute(
                "SELECT sql FROM duckdb_indexes() WHERE schema_name = 'main' AND table_name = ?",
                [table],
            ).fetchall()
        ]
        for table in tables
    }

    con.execute("BEGIN")
    for table in tables:
        con.execute(f'CREATE TEMP TABLE "copy_{table}" AS SELECT * FROM main."{table}"')
    # Children first, because a table that other tables reference cannot be dropped.
    for table in reversed(tables):
        con.execute(f'DROP TABLE main."{table}"')
    for table in tables:
        con.execute(create_sql[table])
        for sql in index_sql[table]:
            con.execute(sql)
        _insert_rows(con=con, table=table)
        con.execute(f'DROP TABLE "copy_{table}"')
    con.execute("COMMIT")


def _create_table_sql(con: duckdb.DuckDBPyConnection, table: str) -> str:
    """Return the CREATE TABLE statement of a table, fixed so that DuckDB can parse it.

    DuckDB does not quote a reserved table name after REFERENCES, for example
    "REFERENCES group(sample_id)". It also writes an empty entry instead of a foreign key
    that references its own table, for example "UNIQUE(name), , FOREIGN KEY ...".
    Rebuild these entries from duckdb_constraints().
    """
    (sql,) = con.execute(
        "SELECT sql FROM duckdb_tables() WHERE schema_name = 'main' AND table_name = ?", [table]
    ).fetchone()
    for (keyword,) in con.execute(
        "SELECT keyword_name FROM duckdb_keywords() WHERE keyword_category = 'reserved'"
    ).fetchall():
        sql = sql.replace(f"REFERENCES {keyword}(", f'REFERENCES "{keyword}"(')
    self_references = _self_references(con=con, table=table)
    if not self_references:
        return sql
    sql = sql.replace(", , ", ", ").replace(", );", ");")
    clauses = [
        f'FOREIGN KEY ("{column}") REFERENCES "{table}"("{referenced}")'
        for column, referenced in self_references
    ]
    assert sql.endswith(");")
    return sql[: -len(");")] + ", " + ", ".join(clauses) + ");"


def _insert_rows(con: duckdb.DuckDBPyConnection, table: str) -> None:
    """Insert the rows of the temp copy into the recreated table.

    A row that references a row of its own table is inserted after that row, because
    DuckDB checks the foreign key against the rows that are already in the table.
    """
    self_references = _self_references(con=con, table=table)
    if not self_references:
        con.execute(f'INSERT INTO main."{table}" SELECT * FROM "copy_{table}"')
        return

    (_, key), *_ = self_references
    ready = " AND ".join(
        f'(c."{column}" IS NULL OR c."{column}" IN (SELECT "{referenced}" FROM main."{table}"))'
        for column, referenced in self_references
    )
    while True:
        (inserted,) = con.execute(
            f'INSERT INTO main."{table}" SELECT * FROM "copy_{table}" c '
            f'WHERE c."{key}" NOT IN (SELECT "{key}" FROM main."{table}") AND {ready}'
        ).fetchone()
        if inserted == 0:
            return


def _self_references(con: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    """Return (column, referenced column) for each foreign key of a table to itself."""
    rows = con.execute(
        "SELECT constraint_column_names, referenced_column_names FROM duckdb_constraints() "
        "WHERE schema_name = 'main' AND constraint_type = 'FOREIGN KEY' "
        "AND table_name = ? AND referenced_table = ?",
        [table, table],
    ).fetchall()
    assert all(len(columns) == 1 for columns, _ in rows), "Only single-column keys are supported"
    return [(columns[0], referenced[0]) for columns, referenced in rows]


def _tables_parents_first(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Return the main tables, each after the tables that its foreign keys reference."""
    tables = [
        name
        for (name,) in con.execute(
            "SELECT table_name FROM duckdb_tables() WHERE schema_name = 'main' ORDER BY 1"
        ).fetchall()
    ]
    parents: dict[str, set[str]] = {table: set() for table in tables}
    for table, referenced in con.execute(
        "SELECT table_name, referenced_table FROM duckdb_constraints() "
        "WHERE schema_name = 'main' AND constraint_type = 'FOREIGN KEY'"
    ).fetchall():
        if table != referenced:
            parents[table].add(referenced)

    ordered: list[str] = []
    while len(ordered) < len(tables):
        ready = [t for t in tables if t not in ordered and parents[t] <= set(ordered)]
        assert ready, "Foreign keys form a cycle"
        ordered.extend(ready)
    return ordered


def _count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    (count,) = con.execute(f'SELECT count(*) FROM main."{table}"').fetchone()
    return int(count)


if __name__ == "__main__":
    main()
