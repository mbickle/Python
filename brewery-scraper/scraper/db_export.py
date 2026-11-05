"""Build SQLite and PostgreSQL artifacts from normalized brewery records.

Both sinks share the same column order and metadata encoding so a snapshot
cannot silently drift between the mobile database and the API database.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scraper.export import load_breweries
from scraper.models import Brewery

BREWERY_COLUMNS = (
    "id",
    "name",
    "brewery_type",
    "street",
    "city",
    "state",
    "state_code",
    "postal_code",
    "country",
    "country_code",
    "website",
    "phone",
    "phone_normalized",
    "latitude",
    "longitude",
    "parent_id",
    "parent_name",
    "record_category",
    "is_craft_brewery",
)

METADATA_COLUMNS = ("key", "value")

SQLITE_SCHEMA = """
CREATE TABLE breweries (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    brewery_type TEXT,
    street TEXT,
    city TEXT,
    state TEXT,
    state_code TEXT,
    postal_code TEXT,
    country TEXT,
    country_code TEXT,
    website TEXT,
    phone TEXT,
    phone_normalized TEXT,
    latitude REAL,
    longitude REAL,
    parent_id TEXT,
    parent_name TEXT,
    record_category TEXT,
    is_craft_brewery INTEGER
        CHECK (is_craft_brewery IN (0, 1) OR is_craft_brewery IS NULL)
) WITHOUT ROWID;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX idx_breweries_lat_lon
    ON breweries (latitude, longitude);

CREATE INDEX idx_breweries_name
    ON breweries (name);

CREATE INDEX idx_breweries_city_state
    ON breweries (city, state);
"""

POSTGRES_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS breweries (
        id TEXT PRIMARY KEY NOT NULL,
        name TEXT NOT NULL,
        brewery_type TEXT,
        street TEXT,
        city TEXT,
        state TEXT,
        state_code TEXT,
        postal_code TEXT,
        country TEXT,
        country_code TEXT,
        website TEXT,
        phone TEXT,
        phone_normalized TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        parent_id TEXT,
        parent_name TEXT,
        record_category TEXT,
        is_craft_brewery BOOLEAN
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY NOT NULL,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_breweries_lat_lon
        ON breweries (latitude, longitude)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_breweries_name
        ON breweries (name)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_breweries_city_state
        ON breweries (city, state)
    """,
)


def brewery_rows(breweries: Sequence[Brewery]) -> list[tuple[Any, ...]]:
    """Return model values in the shared database column order.

    Sorting by ID makes the generated artifacts reproducible regardless of
    the order records happened to arrive in.
    """
    rows = []

    for brewery in sorted(breweries, key=lambda item: item.id):
        values = brewery.model_dump()
        rows.append(tuple(values[column] for column in BREWERY_COLUMNS))

    return rows


def metadata_rows(metadata: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Encode run metadata as sorted key/value rows.

    Values are stored as JSON so strings, numbers, booleans, and nulls keep
    their types when a client reads them back.
    """
    return [
        (key, json.dumps(value, ensure_ascii=False, sort_keys=True))
        for key, value in sorted(metadata.items())
    ]


def export_sqlite(
    breweries: Sequence[Brewery],
    metadata: Mapping[str, Any],
    filename: str | Path,
) -> int:
    """Write a self-contained SQLite database atomically.

    The database is built beside the destination and only moved into place
    after every insert and index succeeds, so a failed export cannot corrupt
    a previously good artifact.
    """
    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = brewery_rows(breweries)
    metadata_values = metadata_rows(metadata)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=str(output_path.parent),
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        _write_sqlite(temporary_path, rows, metadata_values)
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return len(rows)


def _write_sqlite(
    filename: Path,
    rows: Sequence[tuple[Any, ...]],
    metadata_values: Sequence[tuple[str, str]],
) -> None:
    connection = sqlite3.connect(filename)

    try:
        connection.executescript(SQLITE_SCHEMA)

        with connection:
            connection.executemany(
                f"""
                INSERT INTO breweries ({", ".join(BREWERY_COLUMNS)})
                VALUES ({", ".join("?" for _ in BREWERY_COLUMNS)})
                """,
                rows,
            )
            connection.executemany(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                metadata_values,
            )

            actual = connection.execute(
                "SELECT COUNT(*) FROM breweries"
            ).fetchone()[0]

            _require_row_count(actual, len(rows))

        # Give the mobile query planner useful statistics for the three
        # indexes that ship with the artifact.
        connection.execute("ANALYZE")
        connection.commit()
    finally:
        connection.close()


def export_sqlite_from_json(
    input_filename: str | Path,
    output_filename: str | Path,
) -> int:
    """Rebuild an SQLite artifact from a saved brewery JSON export."""
    breweries, metadata = load_breweries(str(input_filename))

    return export_sqlite(breweries, metadata, output_filename)


def export_postgres(
    breweries: Sequence[Brewery],
    metadata: Mapping[str, Any],
    dsn: str,
) -> int:
    """Replace the read-only brewery data in PostgreSQL atomically.

    Rows are copied into a temporary staging table, then inserted into the
    live table inside one transaction. Readers keep seeing the previous
    snapshot until the transaction commits.
    """
    if not dsn or not dsn.strip():
        raise ValueError("PostgreSQL DSN must not be empty")

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL export requires psycopg. "
            "Install the runtime dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    rows = brewery_rows(breweries)
    metadata_values = metadata_rows(metadata)

    with (
        psycopg.connect(dsn) as connection,
        connection.transaction(),
        connection.cursor() as cursor,
    ):
        for statement in POSTGRES_SCHEMA_STATEMENTS:
            cursor.execute(statement)

        cursor.execute(
            """
            CREATE TEMPORARY TABLE breweries_import
            (LIKE breweries INCLUDING DEFAULTS)
            ON COMMIT DROP
            """
        )

        with cursor.copy(_postgres_copy_sql()) as copy:
            for row in rows:
                copy.write_row(row)

        cursor.execute("TRUNCATE TABLE breweries")
        cursor.execute(_postgres_insert_sql())

        cursor.execute("DELETE FROM metadata")

        if metadata_values:
            cursor.executemany(
                "INSERT INTO metadata (key, value) VALUES (%s, %s)",
                metadata_values,
            )

        cursor.execute("SELECT COUNT(*) FROM breweries")
        actual = cursor.fetchone()[0]

        _require_row_count(actual, len(rows))

        # Refresh planner statistics after the bulk replace.
        cursor.execute("ANALYZE breweries")

    return len(rows)


def export_postgres_from_json(
    input_filename: str | Path,
    dsn: str,
) -> int:
    """Load a saved brewery JSON export into PostgreSQL."""
    breweries, metadata = load_breweries(str(input_filename))

    return export_postgres(breweries, metadata, dsn)


def _postgres_copy_sql() -> str:
    columns = ", ".join(BREWERY_COLUMNS)

    return f"COPY breweries_import ({columns}) FROM STDIN"


def _postgres_insert_sql() -> str:
    columns = ", ".join(BREWERY_COLUMNS)

    return (
        f"INSERT INTO breweries ({columns}) "
        f"SELECT {columns} FROM breweries_import"
    )


def _require_row_count(actual: int, expected: int) -> None:
    if actual != expected:
        raise RuntimeError(
            f"database export wrote {actual} rows, expected {expected}"
        )
