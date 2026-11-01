# Brewery Scraper

A Python command-line tool that retrieves brewery-related records from the [Brewers Association](https://www.brewersassociation.org/), normalizes them into a consistent structure, classifies records, and exports JSON datasets, statistics, and optional diagnostic reports.

> **Project status:** Work in progress. Something I started to learn more about Python and because I'm a beerenthusiast.  Maybe I'll expand on this into something else over time.

## What it does

- Fetches the Brewers Association's published JSON data.
- Normalizes source records into `Brewery` models.
- Classifies records into categories such as `brewery`, `brewing_business`, `planning`, `location`, `household`, and `unclassified`.
- Generates summary statistics, including geographic coverage and parent-child relationships.
- Runs named diagnostic reports to investigate data quality and source fields.
- Writes separate JSON files for breweries, statistics, and (when requested) diagnostics.

## Requirements and setup

- Python 3.10 or newer (the model uses `str | None` type annotations).
- Project dependencies include `pydantic` and `rich`. Other dependencies may be required by your local implementation; consult the project's dependency file if present.

From the project root, create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies using the project's dependency file, if one is present. If not, the known core dependencies can be installed with:

```powershell
python -m pip install pydantic rich
```

The normalization code may also require `pycountry`:

```powershell
python -m pip install pycountry
```

## Quick start

From the project root:

```powershell
python main.py
```

By default, this writes:

| File | Contents |
| --- | --- |
| `data/breweries.json` | Shared metadata and normalized brewery records |
| `data/stats.json` | Shared metadata and generated statistics |

Diagnostics are not run unless requested.

## Command-line options

| Option | Description |
| --- | --- |
| `--output PATH` | Brewery JSON output; default `data/breweries.json` |
| `--stats-output PATH` | Statistics JSON output; default `data/breweries-stats.json` |
| `--url URL` | Override the source JSON URL |
| `--list-diagnostics` | Show available diagnostic names without fetching data |
| `--diagnostics NAME [NAME ...]` | Run one or more named reports; use `all` for every registered report |
| `--diagnostics-output PATH` | Diagnostics JSON output; default `data/diagnostics.json` |

Examples:

```powershell
# See available reports
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
```

The available report names are defined in `scraper/diagnostics.py`; `--list-diagnostics` is the authoritative list for your checkout. Running diagnostics also runs the normal brewery and statistics exports. Each diagnostic run overwrites its configured output file.

## Output formats

All three output files include the same run metadata:

```json
{
  "generated_at": "2026-10-31T22:00:00+00:00",
  "source": "Brewers Association",
  "source_url": "https://www.brewersassociation.org/wp-content/themes/ba2019/json-store/breweries/breweries.json",
  "schema_version": "1.0",
  "normalization_version": "1.0",
  "count": 20631,
  "normalized_count": 20631
}
```

The timestamp and counts above are illustrative. `count` is the number of fetched source records; `normalized_count` is the number of normalized records exported.

The brewery file adds a `breweries` array containing normalized model fields. The statistics file adds a `stats` object. The diagnostics file adds a `diagnostics` object keyed by the selected report names. Diagnostic output is only written when `--diagnostics` is supplied.

## Data model and classification

The source JSON uses Salesforce-style field names and nested objects. Normalization converts those records to `Brewery` models with consistent field names, including location, contact details, brewery type, parent references, and a derived `record_category`.

**Important distinctions:**

- `brewery_type` comes from the source; `record_category` is assigned by this project.
- A record categorized as `location` may be associated with a parent organization, but that does not establish independent brewing activity.
- A parent relationship reflects the source's account hierarchy; it is not necessarily proof of legal ownership.
- Missing brewery types and incomplete addresses occur in the source. An `unclassified` record should not automatically be discarded.

Classification rules live in `scraper/classify.py`.

## Diagnostics

Diagnostics are exploratory reports, distinct from the standard statistics generated on every run.

The registry in `scraper/diagnostics.py` separates two kinds of analyses:

- **Raw diagnostics:** receive original source dictionaries from `fetch_url()`.
- **Normalized diagnostics:** receive `Brewery` objects from `normalize_breweries()`.

To add a diagnostic:

1. Write a function that accepts the appropriate dataset and returns JSON-serializable results.
2. Register it in `RAW_DIAGNOSTICS` or `NORMALIZED_DIAGNOSTICS`.
3. Verify its name appears with `python main.py --list-diagnostics`.
4. Run it with `python main.py --diagnostics your-report-name`.

Avoid printing from diagnostic functions; returning structured data keeps reports reusable for JSON export and later analysis. For `Counter` or tuple-keyed results, convert them into JSON-compatible dictionaries or lists before returning.

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
│   └── export.py           # General-purpose JSON writer
└── data/                   # Default generated output files
```

## Data source and limitations

Default source:

```text
https://www.brewersassociation.org/wp-content/themes/ba2019/json-store/breweries/breweries.json
```

This is a third-party published dataset and may change in availability, schema, completeness, and contents. The project is not affiliated with or endorsed by the Brewers Association. Review source terms before redistributing collected data.

## Possible next steps

- Add automated tests for normalization, classification, and diagnostics.
- Add a dependency lockfile or documented `requirements.txt`.
- Add source validation and clearer handling of network failures.
- Introduce optional filters (for example, state or record category).
- Add dataset quality checks and track changes between runs.
- Decide whether to commit generated `data/*.json` files or exclude them in `.gitignore`.
