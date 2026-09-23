"""Seeds a DuckDB with one dataset and one recording for the demo-mcap-server target.

Inserts directly via DuckDB rather than through SQLModel so that the full app
import chain (and the built frontend requirement) is not triggered.

Usage: python demo_mcap_seed.py <db_path> <mcap_uri> <dataset_id> <recording_id>
"""

from __future__ import annotations

import sys
import uuid

import duckdb

_ARGC = 5


def main() -> None:
    """Seeds a DuckDB with one dataset and recording row."""
    if len(sys.argv) != _ARGC:
        print("Usage: demo_mcap_seed.py <db_path> <mcap_uri> <dataset_id> <recording_id>")
        sys.exit(1)

    db_path, mcap_uri, dataset_id_str, recording_id_str = sys.argv[1:]
    dataset_id = uuid.UUID(dataset_id_str)
    recording_id = uuid.UUID(recording_id_str)

    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE IF NOT EXISTS dataset (dataset_id UUID PRIMARY KEY)")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS recording (
            recording_id UUID PRIMARY KEY,
            dataset_id   UUID NOT NULL REFERENCES dataset(dataset_id),
            uri          VARCHAR NOT NULL,
            format       VARCHAR NOT NULL
        )
        """
    )
    con.execute(
        "INSERT OR IGNORE INTO dataset VALUES (?::UUID)",
        [str(dataset_id)],
    )
    con.execute(
        """
        INSERT INTO recording VALUES (?::UUID, ?::UUID, ?, ?)
        ON CONFLICT (recording_id) DO UPDATE SET
            dataset_id = excluded.dataset_id,
            uri = excluded.uri,
            format = excluded.format
        """,
        [str(recording_id), str(dataset_id), mcap_uri, "MCAP"],
    )
    con.close()

    print(f"  dataset_id   = {dataset_id}")
    print(f"  recording_id = {recording_id}")
    print(f"  uri          = {mcap_uri}")


if __name__ == "__main__":
    main()
