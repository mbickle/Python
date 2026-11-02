# AGENTS.md

Project lives in `brewery-scraper/` (Python 3.11+ CLI tool that fetches the Brewers Association JSON dataset, normalizes it to Pydantic `Brewery` models, classifies, stats, and exports JSON). Entry point: `brewery-scraper/main.py` → `scraper.cli.run_cli`.

## Commands

Run from `brewery-scraper/` with the `.venv` venv (Windows scripts, `.venv\Scripts\...`):

```powershell
python -m pytest                      # 70 tests, offline, ~2s — network is monkeypatched
ruff check scraper tests              # must pass before committing
python main.py --list-diagnostics     # safe offline CLI check
python main.py                        # fetches LIVE network data, overwrites data/*.json
```

Verification order: `pytest` → `ruff check` → `--list-diagnostics`.

## Gotchas

- `data/*.json` are committed generated artifacts (the root `.gitignore` does not exclude them). Running `main.py` rewrites them with a new `generated_at` timestamp — don't commit these churns as code changes.
- Tests must stay offline: `tests/test_fetch.py` mocks `requests.get` via `monkeypatch`. Never add tests that hit the real Brewers Association URL.
- `tests/conftest.py` provides a `raw_brewery` fixture factory for realistic Salesforce-shaped source dicts — reuse it instead of crafting raw records inline.
- No project-level tool config exists (no `pyproject.toml`, `ruff.toml`, `pytest.ini`), but ruff still applies a built-in rule set beyond the classic `E`/`F` codes (it flags `UP017`, `BLE001`). Run `ruff check scraper tests` rather than assuming which rules are active.

## Diagnostics convention (from `scraper/diagnostics.py`)

- Two registries: `RAW_DIAGNOSTICS` (accept raw source dicts) vs `NORMALIZED_DIAGNOSTICS` (accept `Brewery` objects). Register new reports in the correct one under a kebab-case name.
- Diagnostic functions must NOT print and must return JSON-serializable data (no `dict`/set keys from `Counter`); `export_json` fails on non-serializable keys.
- Verify with `python main.py --list-diagnostics`, then `python main.py --diagnostics <name>`.

## Docs

`docs/DEVELOPMENT.md`, `docs/CLI.md`, `docs/PIPELINE.md`, `docs/DATA_MODEL.md`, and `docs/DIAGNOSTICS.md` describe the current code. Keep the matching doc in sync when behavior changes: skip-and-report behavior in `PIPELINE.md`, registry entries in `DIAGNOSTICS.md`, options and defaults in `CLI.md`.

`docs/BACKLOG.md` is aspirational — it is not a description of what exists today.
