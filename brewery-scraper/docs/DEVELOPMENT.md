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
| `psycopg[binary]` | `scraper/db_export.py` | PostgreSQL loading; the binary extra bundles libpq |

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

## Local PostgreSQL with Docker

Docker is optional: JSON and SQLite exports work without it. To exercise the PostgreSQL exporter locally, run a disposable Postgres container.

Docker Desktop must be installed, running, and using Linux containers. On Windows, install it once with:

```powershell
winget install -e --id Docker.DockerDesktop
docker run --rm hello-world
```

Start the database:

```powershell
docker run --name brewery-pg `
  -e POSTGRES_DB=breweryfinder `
  -e POSTGRES_USER=brewery `
  -e POSTGRES_PASSWORD=localdev `
  -p 5432:5432 `
  -d postgres:17-alpine
```

Wait until it is ready:

```powershell
docker exec brewery-pg pg_isready -U brewery -d breweryfinder
```

From `scraper/` with the virtual environment active, set the connection string and run the scraper:

```powershell
$env:DATABASE_URL = "postgresql://brewery:localdev@localhost:5432/breweryfinder"
python main.py --postgres-url $env:DATABASE_URL
```

The normal run uses `data/raw/breweries.json` when present, otherwise downloads and caches it, and writes the JSON, SQLite, and PostgreSQL outputs. If `data/breweries.json` already exists and you want to skip the fetch and normalization, use `--input data/breweries.json`.

Verify the load:

```powershell
docker exec brewery-pg psql -U brewery -d breweryfinder -c "\dt"
docker exec brewery-pg psql -U brewery -d breweryfinder -c "select count(*) from breweries;"
```

Stop and remove the disposable database:

```powershell
docker stop brewery-pg
docker rm brewery-pg
```

The container has no volume, so removing it deletes the test data. Add `-v brewery-pg-data:/var/lib/postgresql/data` if you want the data to survive `docker rm`. If port `5432` is already in use, map an unused port such as `-p 5433:5432` and change the URL. The credentials are local-only; never reuse them. For Neon, use the direct/unpooled connection string for this loader and reserve the pooled string for the API.

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
- The database exporter tests use a fake PostgreSQL connection, so `pytest` does not need a running server. For the complete local Docker setup and exporter commands, see [Local PostgreSQL with Docker](#local-postgresql-with-docker). The exporter creates or updates the read-only `breweries` and `metadata` tables; do not point it at a database whose tables you are not prepared to replace.
