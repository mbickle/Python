# AGENTS.md

Project lives in `brewery-scraper/` (Python 3.11+ CLI tool that fetches the Brewers Association JSON dataset, normalizes it to Pydantic `Brewery` models, classifies, stats, and exports JSON). Entry point: `brewery-scraper/main.py` → `scraper.cli.main`, also exposed as the `brewery-scraper` console script via `pyproject.toml`.

## Commands

Run from `brewery-scraper/` with the `.venv` venv (Windows scripts, `.venv\Scripts\...`):

```powershell
python -m pytest                      # offline, ~2s — network is monkeypatched
ruff check scraper tests main.py     # must pass before committing
python main.py --list-diagnostics     # safe offline CLI check
python main.py --input data/breweries.json --stats-output /tmp/stats.json   # offline stats from a local export (run once first)
python main.py                        # reuses data/raw cache (downloads once), overwrites data/*.json
python main.py --refresh              # forces a fresh download before exporting
```

Verification order: `pytest` → `ruff check` → `--list-diagnostics`.

## Gotchas

- Nothing under `data/` is committed: the whole directory is gitignored, including the raw source cache and every export. A fresh clone has no data — the first run downloads it (or pass `--refresh`), and `--input` has nothing to read until then.
- Tests must stay offline: `tests/test_fetch.py` mocks `requests.get` via `monkeypatch`. Never add tests that hit the real Brewers Association URL.
- `data/` is gitignored. Tests that run without `--input`/`--raw-input` must take the `raw_cache` fixture (or monkeypatch `scraper.cli.DEFAULT_RAW_PATH`) or they will write into the real cache path.
- `tests/conftest.py` provides a `raw_brewery` fixture factory for realistic Salesforce-shaped source dicts — reuse it instead of crafting raw records inline.
- Household detection is `is_household()` in `scraper/classify.py`. Classification and the household diagnostics both call it; don't reintroduce substring checks on names.
- `pyproject.toml` holds packaging metadata, the console entry point, and pytest config (`testpaths`, `pythonpath`); runtime dependencies are read from `requirements.txt`, so keep that file authoritative. There is still no ruff config, so ruff applies a built-in rule set beyond the classic `E`/`F` codes (it flags `UP017`, `BLE001`). Run `ruff check scraper tests` rather than assuming which rules are active.

## Diagnostics convention (from `scraper/diagnostics.py`)

- Two registries: `RAW_DIAGNOSTICS` (accept raw source dicts) vs `NORMALIZED_DIAGNOSTICS` (accept `Brewery` objects). Register new reports in the correct one under a kebab-case name.
- Diagnostic functions must NOT print and must return JSON-serializable data (no `dict`/set keys from `Counter`); `export_json` fails on non-serializable keys.
- Verify with `python main.py --list-diagnostics`, then `python main.py --diagnostics <name>`.

## Docs

`docs/DEVELOPMENT.md`, `docs/CLI.md`, `docs/PIPELINE.md`, `docs/DATA_MODEL.md`, and `docs/DIAGNOSTICS.md` describe the current code. Keep the matching doc in sync when behavior changes: skip-and-report behavior in `PIPELINE.md`, registry entries in `DIAGNOSTICS.md`, options and defaults in `CLI.md`.

`docs/BACKLOG.md` is aspirational — it is not a description of what exists today.
