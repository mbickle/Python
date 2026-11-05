import json

import pytest

from scraper.cli import main
from scraper.diagnostics import available_diagnostics


def _record(**overrides):
    record = {
        "id": "001",
        "name": "Alpha Brewing",
        "brewery_type": "Micro",
        "record_category": "brewery",
        "country": "United States",
        "country_code": "US",
        "state": "Washington",
        "state_code": "WA",
    }
    record.update(overrides)
    return record


def _write_export(tmp_path, records):
    payload = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source": "Brewers Association",
        "source_url": "https://example.com/breweries.json",
        "schema_version": "1.0",
        "normalization_version": "1.0",
        "count": len(records),
        "normalized_count": len(records),
        "breweries": records,
    }

    path = tmp_path / "breweries.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    return path


def test_list_diagnostics_prints_names(capsys):
    assert main(["--list-diagnostics"]) == 0

    output = capsys.readouterr().out

    for name in available_diagnostics():
        assert name in output


def test_unknown_diagnostic_rejected(capsys):
    with pytest.raises(SystemExit):
        main(["--diagnostics", "no-such-report"])

    err = capsys.readouterr().err

    assert "Unknown diagnostics" in err
    assert "no-such-report" in err


def test_all_keyword_runs_live_fetch(monkeypatch, tmp_path, raw_cache):
    called = {}

    def fake_fetch(url):
        called["url"] = url
        return []

    monkeypatch.setattr("scraper.cli.fetch_url", fake_fetch)

    result = main([
        "--diagnostics", "all",
        "--output", str(tmp_path / "b.json"),
        "--stats-output", str(tmp_path / "s.json"),
        "--sqlite-output", str(tmp_path / "breweries.db"),
        "--diagnostics-output", str(tmp_path / "d.json"),
    ])

    assert result == 0
    assert called["url"].startswith("https://")
    # An empty response must not create or overwrite the cache.
    assert not raw_cache.exists()


def test_input_mode_skips_fetch_and_brewery_export(
    monkeypatch, tmp_path, capsys
):
    source = _write_export(tmp_path, [_record()])

    def explode(url):
        raise AssertionError("--input must not fetch")

    monkeypatch.setattr("scraper.cli.fetch_url", explode)

    output = tmp_path / "out.json"
    stats_output = tmp_path / "stats.json"
    sqlite_output = tmp_path / "breweries.db"

    assert main([
        "--input", str(source),
        "--output", str(output),
        "--stats-output", str(stats_output),
        "--sqlite-output", str(sqlite_output),
    ]) == 0

    assert not output.exists()
    assert sqlite_output.exists()

    payload = json.loads(stats_output.read_text(encoding="utf-8"))

    assert payload["stats"]["total_breweries"] == 1
    assert payload["stats"]["top_states"] == {"WA": 1}
    assert payload["input"] == str(source)
    assert payload["source"] == "Brewers Association"
    assert payload["count"] == 1


def test_input_mode_runs_normalized_diagnostics(tmp_path):
    source = _write_export(tmp_path, [_record()])
    diagnostics_output = tmp_path / "diag.json"

    assert main([
        "--input", str(source),
        "--diagnostics", "parent-coverage",
        "--output", str(tmp_path / "o.json"),
        "--stats-output", str(tmp_path / "s.json"),
        "--sqlite-output", str(tmp_path / "breweries.db"),
        "--diagnostics-output", str(diagnostics_output),
    ]) == 0

    payload = json.loads(diagnostics_output.read_text(encoding="utf-8"))

    assert "parent-coverage" in payload["diagnostics"]


@pytest.mark.parametrize("name", ["raw-record-types", "all"])
def test_input_mode_rejects_raw_diagnostics(name, tmp_path, capsys):
    source = _write_export(tmp_path, [_record()])

    with pytest.raises(SystemExit):
        main(["--input", str(source), "--diagnostics", name])

    err = capsys.readouterr().err

    assert "raw diagnostics" in err


def test_input_and_url_conflict(tmp_path, capsys):
    source = _write_export(tmp_path, [_record()])

    with pytest.raises(SystemExit):
        main(["--input", str(source), "--url", "https://example.com/x.json"])

    assert "--input cannot be combined with --url" in capsys.readouterr().err


def test_input_file_must_exist(tmp_path, capsys):
    missing = tmp_path / "missing.json"

    with pytest.raises(SystemExit) as excinfo:
        main(["--input", str(missing)])

    assert excinfo.value.code == 2

    err = capsys.readouterr().err
    assert f"--input file not found: {missing}" in err
    assert "Run without --input" in err
    assert "Traceback" not in err


@pytest.fixture
def raw_cache(monkeypatch, tmp_path):
    """Keep the raw cache in tmp_path so tests never touch data/raw/."""
    path = tmp_path / "raw" / "breweries.json"
    monkeypatch.setattr("scraper.cli.DEFAULT_RAW_PATH", str(path))

    return path


def _raw_record(**overrides):
    record = {
        "Id": "001",
        "Name": "Alpha Brewing",
        "Brewery_Type__c": "Micro",
        "BillingAddress": {
            "country": "United States",
            "stateCode": "WA",
        },
        "Is_Craft_Brewery__c": True,
    }
    record.update(overrides)

    return record


def _paths(tmp_path):
    return [
        "--output", str(tmp_path / "breweries.json"),
        "--stats-output", str(tmp_path / "stats.json"),
        "--sqlite-output", str(tmp_path / "breweries.db"),
    ]


def test_first_run_downloads_and_caches(monkeypatch, tmp_path, raw_cache):
    calls = {"n": 0}

    def fake_fetch(url):
        calls["n"] += 1
        return [_raw_record()]

    monkeypatch.setattr("scraper.cli.fetch_url", fake_fetch)

    assert main(_paths(tmp_path)) == 0

    assert calls["n"] == 1
    assert raw_cache.exists()

    payload = json.loads((tmp_path / "stats.json").read_text(encoding="utf-8"))
    assert payload["raw_source"] == str(raw_cache)
    assert payload["raw_fetched_at"]


def test_second_run_reuses_cache(monkeypatch, tmp_path, raw_cache):
    raw_cache.parent.mkdir(parents=True, exist_ok=True)
    raw_cache.write_text(json.dumps([_raw_record()]), encoding="utf-8")

    def explode(url):
        raise AssertionError("cache should be reused")

    monkeypatch.setattr("scraper.cli.fetch_url", explode)

    assert main(_paths(tmp_path)) == 0

    payload = json.loads((tmp_path / "stats.json").read_text(encoding="utf-8"))
    assert payload["raw_source"] == str(raw_cache)


def test_refresh_downloads_again(monkeypatch, tmp_path, raw_cache):
    raw_cache.parent.mkdir(parents=True, exist_ok=True)
    raw_cache.write_text(
        json.dumps([_raw_record(Name="Cached Brewing")]),
        encoding="utf-8",
    )

    def fake_fetch(url):
        return [
            _raw_record(Name="Fresh Brewing"),
            _raw_record(Id="002", Name="Second Brewing"),
        ]

    monkeypatch.setattr("scraper.cli.fetch_url", fake_fetch)

    assert main([*_paths(tmp_path), "--refresh"]) == 0

    payload = json.loads((tmp_path / "stats.json").read_text(encoding="utf-8"))
    assert payload["stats"]["total_breweries"] == 2
    assert "Fresh Brewing" in raw_cache.read_text(encoding="utf-8")


def test_raw_input_runs_raw_diagnostics_offline(monkeypatch, tmp_path):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps([_raw_record()]), encoding="utf-8")

    def explode(url):
        raise AssertionError("--raw-input must not fetch")

    monkeypatch.setattr("scraper.cli.fetch_url", explode)

    diagnostics_output = tmp_path / "diag.json"

    assert main([
        "--raw-input", str(snapshot),
        "--diagnostics", "raw-record-types",
        *_paths(tmp_path),
        "--diagnostics-output", str(diagnostics_output),
    ]) == 0

    payload = json.loads(diagnostics_output.read_text(encoding="utf-8"))
    assert "raw-record-types" in payload["diagnostics"]
    assert payload["raw_source"] == str(snapshot)
    assert payload["source"] is None
    assert payload["source_url"] is None


@pytest.mark.parametrize(
    "extra",
    [["--refresh"], ["--url", "https://example.com/x.json"]],
)
def test_raw_input_rejects_conflicting_flags(extra, tmp_path, capsys):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("[]", encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["--raw-input", str(snapshot), *extra])

    assert "--raw-input cannot be combined" in capsys.readouterr().err


def test_input_rejects_raw_input(tmp_path, capsys):
    source = _write_export(tmp_path, [_record()])

    with pytest.raises(SystemExit):
        main(["--input", str(source), "--raw-input", "other.json"])

    err = capsys.readouterr().err
    assert "--input cannot be combined with --raw-input" in err


def test_input_rejects_refresh(tmp_path, capsys):
    source = _write_export(tmp_path, [_record()])

    with pytest.raises(SystemExit):
        main(["--input", str(source), "--refresh"])

    err = capsys.readouterr().err
    assert "--input cannot be combined with --refresh" in err


def test_skip_sqlite_does_not_write_database(tmp_path):
    source = _write_export(tmp_path, [_record()])

    assert main([
        "--input", str(source),
        "--skip-sqlite",
        "--stats-output", str(tmp_path / "stats.json"),
    ]) == 0

    assert not (tmp_path / "breweries.db").exists()


def test_postgres_url_exports_loaded_records(monkeypatch, tmp_path):
    source = _write_export(tmp_path, [_record()])
    sqlite_output = tmp_path / "breweries.db"
    called = {}

    def fake_export_postgres(breweries, metadata, dsn):
        called["breweries"] = breweries
        called["metadata"] = metadata
        called["dsn"] = dsn

    monkeypatch.setattr(
        "scraper.cli.export_postgres",
        fake_export_postgres,
    )

    assert main([
        "--input", str(source),
        "--sqlite-output", str(sqlite_output),
        "--postgres-url", "postgresql://example/test",
        "--stats-output", str(tmp_path / "stats.json"),
    ]) == 0

    assert len(called["breweries"]) == 1
    assert called["metadata"]["schema_version"] == "1.0"
    assert called["metadata"]["input"] == str(source)
    assert called["dsn"] == "postgresql://example/test"
    assert sqlite_output.exists()


def test_empty_source_response_does_not_overwrite_the_cache(
    monkeypatch, tmp_path, raw_cache
):
    raw_cache.parent.mkdir(parents=True, exist_ok=True)
    raw_cache.write_text(json.dumps([_raw_record()]), encoding="utf-8")
    before = raw_cache.read_text(encoding="utf-8")

    monkeypatch.setattr("scraper.cli.fetch_url", lambda url: [])

    assert main([*_paths(tmp_path), "--refresh"]) == 0

    assert raw_cache.read_text(encoding="utf-8") == before

    payload = json.loads((tmp_path / "stats.json").read_text(encoding="utf-8"))
    assert payload["stats"]["total_breweries"] == 0
    assert "raw_source" not in payload
