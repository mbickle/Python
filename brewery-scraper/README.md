# Brewery Scraper

A Python command-line tool that retrieves brewery records from the [Brewers Association](https://www.brewersassociation.org/), normalizes them into a consistent structure, classifies them, and exports JSON datasets, statistics, optional diagnostic reports, and read-only SQLite/PostgreSQL database artifacts.

> **Project status:** Work in progress. A learning project — Python practice from someone who likes beer. May grow into a bigger brewery-finder app over time.

## What it does

- Fetches the Brewers Association's published JSON data, caching the download under `data/raw/` (gitignored) so later runs reuse it instead of re-fetching.
- Normalizes source records into `Brewery` models (see `docs/DATA_MODEL.md`).
- Classifies records into categories such as `brewery`, `brewing_business`, `planning`, `location`, `household`, and `unclassified`.
- Generates summary statistics, including geographic coverage and parent-child relationships.
- Runs named diagnostic reports to investigate data quality (see `docs/DIAGNOSTICS.md`).
- Writes separate JSON files for breweries, statistics, and (when requested) diagnostics.
- Writes `data/breweries.db` by default, plus an optional PostgreSQL copy when a DSN is supplied.

## Quick start

Requirements: Python 3.11+, plus the packages in `requirements-dev.txt` (installed by `pip-install.cmd`). Full setup instructions live in `docs/DEVELOPMENT.md`, including the [local PostgreSQL/Docker commands](docs/DEVELOPMENT.md#local-postgresql-with-docker).

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python main.py
```

Or install it as a command (`pip install -e .`), then run `brewery-scraper` from the project directory — output and cache paths are relative to the current directory.

By default, this writes:

| File | Contents |
| --- | --- |
| `data/breweries.json`       | Shared metadata and normalized brewery records |
| `data/breweries-stats.json` | Shared metadata and generated statistics |
| `data/breweries.db`         | Read-only SQLite database for the mobile app |

Diagnostics are not run unless requested. The SQLite file is written on every run; pass `--skip-sqlite` when you only need JSON.

## Command-line options

| Option | Description |
| --- | --- |
| `--output PATH` | Brewery JSON output; default `data/breweries.json` |
| `--stats-output PATH` | Statistics JSON output; default `data/breweries-stats.json` |
| `--sqlite-output PATH` | SQLite database output; default `data/breweries.db` |
| `--skip-sqlite` | Skip the SQLite database export |
| `--postgres-url DSN` | Also load the snapshot into PostgreSQL; omitted by default |
| `--url URL` | Override the source JSON URL |
| `--input PATH` | Reuse an existing brewery export instead of fetching; still runs stats, diagnostics, and database exports |
| `--raw-input PATH` | Use a saved raw source snapshot instead of downloading; supports every diagnostic |
| `--refresh` | Download the source again instead of using the cached copy |
| `--list-diagnostics` | Show available diagnostic names without fetching data |
| `--diagnostics NAME [NAME ...]` | Run one or more named reports; use `all` for every registered report |
| `--diagnostics-output PATH` | Diagnostics JSON output; default `data/diagnostics.json` |

Examples:

```powershell
# See available reports
python main.py --list-diagnostics

# Run a single report
python main.py --diagnostics parent-coverage

# Run every registered report
python main.py --diagnostics all

# Rebuild the SQLite artifact from an existing JSON snapshot
python main.py --input data/breweries.json --sqlite-output data/breweries.db

# Also load PostgreSQL (PowerShell)
$env:DATABASE_URL = "postgresql://user:password@host/dbname"
python main.py --postgres-url $env:DATABASE_URL
```

Full CLI reference: `docs/CLI.md`.

## Project layout

```text
brewery-scraper/
├── main.py                 # CLI entry point
├── scraper/
│   ├── cli.py              # Arguments and orchestration
│   ├── fetch.py            # Download source records
│   ├── models.py           # Pydantic Brewery model
│   ├── normalize.py        # Source-to-model transformation
│   ├── classify.py         # Derived record categories
│   ├── stats.py            # Regular summary statistics
│   ├── diagnostics.py      # Optional investigative reports
│   ├── db_export.py        # SQLite and PostgreSQL exporters
│   └── export.py           # JSON read/write helpers
├── tests/                  # pytest test suite
├── docs/                   # Detailed documentation
└── data/                   # Generated exports + raw cache (gitignored)
```

How the pieces fit together: `docs/PIPELINE.md`.

## Data source and limitations

Default source:

```text
https://www.brewersassociation.org/wp-content/themes/ba2019/json-store/breweries/breweries.json
```

This is a third-party published dataset and may change in availability, schema, completeness, and contents. The project is not affiliated with or endorsed by the Brewers Association. Review source terms before redistributing collected data.

## Docs

| Doc | Contents |
| --- | --- |
| `docs/DEVELOPMENT.md` | Environment setup, dependencies, running tests and lint |
| `docs/PIPELINE.md` | How data flows through the modules |
| `docs/DATA_MODEL.md` | Output file formats, the `Brewery` model, classification rules |
| `docs/CLI.md` | Full command-line reference with examples |
| `docs/DIAGNOSTICS.md` | How diagnostics work and how to add one |
| `docs/BACKLOG.md` | Backlog of ideas and future work |

## Possible next steps

- Pin dependency versions or add a lockfile; `requirements.txt` lists names only.
- Add source validation and clearer handling of network failures.
- Introduce optional filters (for example, state or record category).
- Add dataset quality checks and track changes between runs.
