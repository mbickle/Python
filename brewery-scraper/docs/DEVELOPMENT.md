# Development setup

## Requirements

- Python 3.11 or newer (`scraper/cli.py` uses `datetime.UTC`; the model uses `str | None` type annotations).
- Windows PowerShell examples below; adjust paths for other shells.

## Environment

From the project root, create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Dependencies

Runtime dependencies live in `requirements.txt`; dev dependencies (testing and lint) live in `requirements-dev.txt`, which includes the runtime file. The runtime packages, based on what the code actually imports, are:

| Package | Used by | Purpose |
| --- | --- | --- |
| `requests` | `scraper/fetch.py` | Downloading the source JSON |
| `rich` | `scraper/cli.py`, `scraper/fetch.py`, `scraper/normalize.py` | Terminal output, progress, and skip warnings |
| `pydantic` | `scraper/models.py` | The `Brewery` data model and validation |
| `phonenumbers` | `scraper/normalize.py` | Phone number parsing and E.164 formatting |
| `pycountry` | `scraper/normalize.py` | Country name to ISO alpha-2 code lookup |

```powershell
python -m pip install -r requirements-dev.txt
```

`pip-install.cmd` runs that same command, so one step installs runtime and dev packages.

## Installing the package

`pyproject.toml` declares the package, the `brewery-scraper` console entry point, and the pytest configuration (`testpaths`, `pythonpath`). Runtime dependencies are read from `requirements.txt`, so that file remains the place to change versions.

```powershell
pip install -e .
brewery-scraper --list-diagnostics
```

An editable install is optional: `python main.py` works without it and is what the docs and scripts use. `init.cmd` creates `.venv`, activates it, and calls `pip-install.cmd`; both scripts resolve paths relative to their own location, so they work from any directory.

## Running the tests

```powershell
python -m pytest
```

With a coverage report:

```powershell
python -m pytest --cov=scraper --cov-report=term-missing
```

## Linting

```powershell
ruff check scraper tests
```

## Notes

- Default CLI output paths use forward slashes (`data/breweries.json`, `data/breweries-stats.json`, `data/diagnostics.json`), so they work on any platform.
- Nothing under `data/` is tracked: the raw source cache and every generated export are gitignored. The first run downloads the source (or pass `--refresh`); after that `python main.py` reuses `data/raw/breweries.json`.
- Tests must point `scraper.cli.DEFAULT_RAW_PATH` at `tmp_path` so they never write into the real cache path.
