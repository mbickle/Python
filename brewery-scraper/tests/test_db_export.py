import json
import sqlite3
import sys
import types
from contextlib import closing

import pytest

from scraper.db_export import (
    BREWERY_COLUMNS,
    POSTGRES_SCHEMA_STATEMENTS,
    export_postgres,
    export_sqlite,
    export_sqlite_from_json,
    metadata_rows,
)
from scraper.export import export_json
from scraper.models import Brewery


def _brewery(identifier="001", **overrides):
    values = {
        "id": identifier,
        "name": "Alpha Brewing",
        "brewery_type": "Micro",
        "street": "1 Main St",
        "city": "Seattle",
        "state": "Washington",
        "state_code": "WA",
        "postal_code": "98101",
        "country": "United States",
        "country_code": "US",
        "website": "https://alpha.example",
        "phone": "+12065550100",
        "phone_normalized": "+12065550100",
        "latitude": 47.6062,
        "longitude": -122.3321,
        "parent_id": None,
        "parent_name": None,
        "record_category": "brewery",
        "is_craft_brewery": True,
    }
    values.update(overrides)

    return Brewery(**values)


def _metadata(count=2):
    return {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source": "Brewers Association",
        "source_url": "https://example.com/breweries.json",
        "raw_source": "data/raw/breweries.json",
        "raw_fetched_at": "2025-12-31T23:00:00+00:00",
        "schema_version": "1.0",
        "normalization_version": "1.0",
        "count": count,
        "normalized_count": count,
    }


def test_export_sqlite_writes_schema_rows_and_metadata(tmp_path):
    target = tmp_path / "breweries.db"
    breweries = [
        _brewery("002", name="Beta Brewing", is_craft_brewery=False),
        _brewery("001"),
        _brewery(
            "003",
            name="Gamma Brewing",
            latitude=None,
            longitude=None,
            is_craft_brewery=None,
        ),
    ]

    written = export_sqlite(breweries, _metadata(3), target)

    assert written == 3

    with closing(sqlite3.connect(target)) as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info('breweries')")
        ]
        rows = connection.execute(
            """
            SELECT id, name, is_craft_brewery, latitude, longitude
            FROM breweries
            ORDER BY id
            """
        ).fetchall()
        indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list('breweries')")
        }
        metadata = dict(
            connection.execute("SELECT key, value FROM metadata")
        )

    assert columns == list(BREWERY_COLUMNS)
    assert rows == [
        ("001", "Alpha Brewing", 1, 47.6062, -122.3321),
        ("002", "Beta Brewing", 0, 47.6062, -122.3321),
        ("003", "Gamma Brewing", None, None, None),
    ]
    assert {
        "idx_breweries_lat_lon",
        "idx_breweries_name",
        "idx_breweries_city_state",
    } <= indexes

    assert json.loads(metadata["schema_version"]) == "1.0"
    assert json.loads(metadata["count"]) == 3
    assert json.loads(metadata["normalized_count"]) == 3
    assert json.loads(metadata["source"]) == "Brewers Association"
    assert json.loads(metadata["raw_fetched_at"]).startswith("2025-12-31")


def test_export_sqlite_can_query_by_coordinates(tmp_path):
    target = tmp_path / "breweries.db"
    export_sqlite(
        [_brewery("001"), _brewery("002", latitude=None, longitude=None)],
        _metadata(2),
        target,
    )

    with closing(sqlite3.connect(target)) as connection:
        rows = connection.execute(
            """
            SELECT id
            FROM breweries
            WHERE latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            """,
            (47.0, 48.0, -123.0, -122.0),
        ).fetchall()

    assert rows == [("001",)]


def test_export_sqlite_preserves_previous_artifact_on_failure(tmp_path):
    target = tmp_path / "breweries.db"
    target.write_text("previous artifact", encoding="utf-8")

    with pytest.raises(sqlite3.IntegrityError):
        export_sqlite(
            [_brewery("001"), _brewery("001", name="Duplicate")],
            _metadata(2),
            target,
        )

    assert target.read_text(encoding="utf-8") == "previous artifact"
    assert not list(tmp_path.glob(".breweries.db.*.tmp"))


def test_export_sqlite_from_json_rebuilds_artifact(tmp_path):
    source = tmp_path / "breweries.json"
    target = tmp_path / "breweries.db"
    payload = {
        **_metadata(1),
        "breweries": [_brewery().model_dump()],
    }
    export_json(payload, source)

    assert export_sqlite_from_json(source, target) == 1

    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute(
            "SELECT name FROM breweries"
        ).fetchone() == ("Alpha Brewing",)
        assert json.loads(
            connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()[0]
        ) == "1.0"


def test_brewery_columns_match_the_model():
    assert BREWERY_COLUMNS == tuple(Brewery.model_fields)


def test_metadata_rows_are_sorted_and_json_encoded():
    rows = metadata_rows({
        "normalized_count": 1,
        "source": None,
        "schema_version": "1.0",
        "count": 1,
    })

    assert [key for key, _ in rows] == [
        "count",
        "normalized_count",
        "schema_version",
        "source",
    ]
    assert json.loads(dict(rows)["source"]) is None
    assert json.loads(dict(rows)["count"]) == 1


class _FakeCopy:
    def __init__(self):
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def write_row(self, row):
        self.rows.append(tuple(row))


class _FakeCursor:
    def __init__(self):
        self.statements = []
        self.copy_sql = None
        self.copy_rows = []
        self.executemany_calls = []
        self._result = (2,)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params=None):
        self.statements.append(" ".join(statement.split()))

    def copy(self, statement):
        self.copy_sql = " ".join(statement.split())
        self.copy = _FakeCopy()

        return self.copy

    def executemany(self, statement, values):
        self.executemany_calls.append(
            (" ".join(statement.split()), list(values))
        )

    def fetchone(self):
        return self._result


class _FakeConnection:
    def __init__(self):
        self.cursor_instance = _FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def transaction(self):
        return self

    def cursor(self):
        return self.cursor_instance


def test_export_postgres_stages_rows_and_swaps(monkeypatch):
    connection = _FakeConnection()
    calls = {}

    def connect(dsn):
        calls["dsn"] = dsn
        return connection

    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.connect = connect
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    breweries = [
        _brewery("002", name="Beta Brewing"),
        _brewery("001"),
    ]

    assert export_postgres(
        breweries, _metadata(2), "postgresql://example/test"
    ) == 2

    cursor = connection.cursor_instance

    assert calls["dsn"] == "postgresql://example/test"
    assert len([s for s in cursor.statements if "CREATE TABLE" in s]) == 2
    assert cursor.copy_sql == (
        "COPY breweries_import ("
        + ", ".join(BREWERY_COLUMNS)
        + ") FROM STDIN"
    )
    assert cursor.copy.rows == [
        tuple(getattr(breweries[1], column) for column in BREWERY_COLUMNS),
        tuple(getattr(breweries[0], column) for column in BREWERY_COLUMNS),
    ]
    assert "TRUNCATE TABLE breweries" in cursor.statements
    assert any(
        statement.startswith("INSERT INTO breweries (")
        for statement in cursor.statements
    )
    assert any(
        statement.startswith("DELETE FROM metadata")
        for statement in cursor.statements
    )
    assert cursor.executemany_calls
    assert "INSERT INTO metadata" in cursor.executemany_calls[0][0]
    assert json.loads(
        dict(cursor.executemany_calls[0][1])["schema_version"]
    ) == "1.0"


def test_export_postgres_rejects_row_count_mismatch(monkeypatch):
    connection = _FakeConnection()
    connection.cursor_instance._result = (1,)

    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.connect = lambda dsn: connection
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    with pytest.raises(RuntimeError, match="wrote 1 rows, expected 2"):
        export_postgres(
            [_brewery("001"), _brewery("002")],
            _metadata(2),
            "postgresql://example/test",
        )


def test_export_postgres_requires_psycopg(monkeypatch):
    monkeypatch.setitem(sys.modules, "psycopg", None)

    with pytest.raises(RuntimeError, match="requires psycopg"):
        export_postgres([_brewery()], _metadata(1), "postgresql://example/test")


def test_export_postgres_rejects_empty_dsn():
    with pytest.raises(ValueError, match="must not be empty"):
        export_postgres([_brewery()], _metadata(1), "  ")


def test_postgres_schema_declares_expected_columns():
    schema = " ".join(POSTGRES_SCHEMA_STATEMENTS)

    for column in BREWERY_COLUMNS:
        assert column in schema
