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


def test_all_keyword_runs_live_fetch(monkeypatch, tmp_path):
    called = {}

    def fake_fetch(url):
        called["url"] = url
        return []

    monkeypatch.setattr("scraper.cli.fetch_url", fake_fetch)

    result = main([
        "--diagnostics", "all",
        "--output", str(tmp_path / "b.json"),
        "--stats-output", str(tmp_path / "s.json"),
        "--diagnostics-output", str(tmp_path / "d.json"),
    ])

    assert result == 0
    assert called["url"].startswith("https://")


def test_input_mode_skips_fetch_and_brewery_export(
    monkeypatch, tmp_path, capsys
):
    source = _write_export(tmp_path, [_record()])

    def explode(url):
        raise AssertionError("--input must not fetch")

    monkeypatch.setattr("scraper.cli.fetch_url", explode)

    output = tmp_path / "out.json"
    stats_output = tmp_path / "stats.json"

    assert main([
        "--input", str(source),
        "--output", str(output),
        "--stats-output", str(stats_output),
    ]) == 0

    assert not output.exists()

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
