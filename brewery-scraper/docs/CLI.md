# Command-line reference

```powershell
python main.py [options]
```

## Options

| Option | Description |
| --- | --- |
| `--output PATH` | Brewery JSON output; default `data/breweries.json` |
| `--stats-output PATH` | Statistics JSON output; default `data/breweries-stats.json` |
| `--sqlite-output PATH` | SQLite database output; default `data/breweries.db` |
| `--skip-sqlite` | Skip the SQLite database export |
| `--postgres-url DSN` | Also load the snapshot into PostgreSQL; omitted by default |
| `--url URL` | Override the source JSON URL |
| `--input PATH` | Reuse an existing brewery export; the file must already exist; skips fetching and the JSON brewery export |
| `--raw-input PATH` | Use a saved raw source snapshot instead of downloading |
| `--refresh` | Download the source again instead of using the cached copy |
| `--list-diagnostics` | Show available diagnostic names without fetching data |
| `--diagnostics NAME [NAME ...]` | Run one or more named reports; use `all` for every registered report |
| `--diagnostics-output PATH` | Diagnostics JSON output; default `data/diagnostics.json` |

## Examples

```powershell
# See available reports (no data is fetched)
python main.py --list-diagnostics

# Run a single report
python main.py --diagnostics parent-coverage

# Run several reports
python main.py --diagnostics parent-coverage household-records

# Run every registered report
python main.py --diagnostics all

# Choose output locations
python main.py --output data/breweries.json --stats-output data/stats.json

# Save diagnostics to a different file
python main.py --diagnostics us-region-issues --diagnostics-output reports/regions.json

# Reuse an export from a previous run: no network, writes stats only
python main.py --input data/breweries.json --stats-output data/stats.json

# Normalized diagnostics against an existing export
python main.py --input data/breweries.json --diagnostics household-records

# Reuse the cached download (the default when data/raw/breweries.json exists)
python main.py

# Force a fresh download
python main.py --refresh

# Inspect a saved snapshot, including raw diagnostics
python main.py --raw-input data/raw/breweries.json --diagnostics raw-record-types

# Use a different source URL
python main.py --url https://example.com/breweries.json

# Rebuild SQLite from an existing JSON export, with no network request
python main.py --input data/breweries.json --sqlite-output data/breweries.db

# Also load PostgreSQL (PowerShell)
$env:DATABASE_URL = "postgresql://user:password@host/dbname"
python main.py --postgres-url $env:DATABASE_URL

# Write JSON and stats without a SQLite artifact
python main.py --skip-sqlite
```

## Behavior notes

- Diagnostic names are validated before any data is fetched; unknown names cause an error.
- The available report names are defined in `scraper/diagnostics.py`; `--list-diagnostics` is the authoritative list for your checkout.
- Running diagnostics also runs the normal brewery and statistics exports (with `--input`, the brewery export is skipped).
- `--input` reads a file written by `--output` and performs no network request. The file must already exist; if it is missing, the command exits with `--input file not found` instead of falling back to a download. Run without `--input` to create a fresh snapshot. Because an input file holds only normalized records, raw diagnostics cannot run from it and `all` is rejected; name normalized reports individually.
- `--input` can still write the SQLite and PostgreSQL artifacts, so it is the way to rebuild a database from a saved snapshot.
- `--input` cannot be combined with `--url` or `--raw-input`.
- The SQLite database is written by default to `data/breweries.db`; use `--skip-sqlite` to omit it or `--sqlite-output` to choose another path. The file is replaced atomically, so a failed export leaves the previous artifact intact.
- `--postgres-url` is opt-in. When set, the exporter stages rows in a temporary table and replaces the live `breweries` and `metadata` rows in one transaction. The connection string is never printed.
- Metadata values in both databases are stored as JSON strings so `null`, numbers, and booleans keep their types.
- The raw source is cached at `data/raw/breweries.json`, which is gitignored. When it exists, runs reuse it and make no network request; `--refresh` or `--url` downloads again.
- `--raw-input PATH` reads a specific snapshot instead of the cache. Unlike `--input`, it supports every registered diagnostic, including the raw ones.
- `--raw-input` cannot be combined with `--refresh` or `--url`.
- Each export records `raw_source` and `raw_fetched_at`, so a stale run is visible in the output. `source_url` is `null` when the data came from `--raw-input`.
- Each run overwrites its configured output files.
- If the fetch fails after all retries, the program exits with an error and no files are written.
