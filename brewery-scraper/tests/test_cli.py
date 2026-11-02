import pytest

from scraper.cli import run_cli
from scraper.diagnostics import available_diagnostics


def test_list_diagnostics_prints_names(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv", ["main.py", "--list-diagnostics"]
    )

    run_cli()  # returns without fetching

    output = capsys.readouterr().out
    for name in available_diagnostics():
        assert name in output


def test_unknown_diagnostic_rejected(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv", ["main.py", "--diagnostics", "no-such-report"]
    )

    with pytest.raises(SystemExit):
        run_cli()

    err = capsys.readouterr().err
    assert "Unknown diagnostics" in err
    assert "no-such-report" in err


def test_all_keyword_passes_validation(monkeypatch):
    # 'all' is special-cased and must not be treated as unknown.
    # Patch fetch_url so no network call happens, then stop the
    # run before it does real work by checking validation passed.
    monkeypatch.setattr(
        "sys.argv", ["main.py", "--diagnostics", "all"]
    )

    called = {}

    def fake_fetch(url):
        called["url"] = url
        return []

    monkeypatch.setattr("scraper.cli.fetch_url", fake_fetch)
    monkeypatch.setattr(
        "scraper.cli.export_json", lambda data, path: None
    )

    run_cli()  # should not raise SystemExit

    assert called["url"].startswith("https://")
