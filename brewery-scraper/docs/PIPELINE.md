# Pipeline

How data flows through the tool, from download to output files.

```text
data/raw cache ──┐
--raw-input ─────┼──► normalize_breweries() ──► generate_stats() ──► export_json()
fetch_url() ─────┘      (normalize.py)            (stats.py)          (export.py)
                       │
                       ▼
              classify_brewery()
                (classify.py)

  optional: run_diagnostics() ──► export_json()
              (diagnostics.py)
```

## Stages

### Source acquisition (cache, `--refresh`, `--raw-input`)

Before anything else, the raw source is resolved (`_acquire_raw_data` in `scraper/cli.py`):

- `--raw-input PATH` reads that snapshot with `load_raw_records()` and never touches the network.
- Otherwise, if the cache at `data/raw/breweries.json` exists and neither `--refresh` nor `--url` is given, the cache is loaded and nothing is downloaded.
- Otherwise `fetch_url()` downloads the source and `save_raw_records()` overwrites the cache with a compact JSON copy.

The chosen file and its timestamp are recorded in the export metadata as `raw_source` and `raw_fetched_at`. Because this data is the original source dictionaries, both diagnostic registries can run from it, so raw diagnostics work offline.

### 0. Optional input (`--input`)

With `--input PATH`, the fetch and normalize stages are skipped entirely. `load_breweries()` (`scraper/export.py`) reads a file previously written by `--output`, rebuilds `Brewery` objects from its `breweries` array, and returns the run metadata that came with it. Statistics and normalized diagnostics then run as usual, and the brewery export is skipped because the records already came from that file. Raw diagnostics are rejected, since a saved export holds no source dictionaries.

### 1. Fetch (`scraper/fetch.py`)

`fetch_url(url)` downloads the source JSON with `requests` (30-second timeout), retrying up to 3 times with a 1-second delay between attempts. It validates that the response is a JSON array of objects and raises if the structure is unexpected. It only runs when the cache is missing, `--refresh` is given, or `--url` overrides the source.

### 2. Normalize (`scraper/normalize.py`)

`normalize_breweries(raw_data)` converts each raw Salesforce-style record into a `Brewery` pydantic model (`scraper/models.py`):

- Text fields are stripped; empty or whitespace-only values become `None` (`clean_text`).
- Geographic codes are uppercased (`normalize_code`).
- Country names are resolved to ISO alpha-2 codes via `pycountry`, with a small override table (`COUNTRY_OVERRIDES`) for names `pycountry` doesn't recognize.
- Phone numbers are parsed with `phonenumbers` and formatted as E.164 when valid (`normalize_phone`).
- Parent organization info is pulled from the nested `Parent` object.

Each record is then classified (next stage) before being added to the result list.

### 3. Classify (`scraper/classify.py`)

`classify_brewery(brewery)` assigns a `record_category` derived from the source's `brewery_type`:

| Source `brewery_type` | `record_category` |
| --- | --- |
| Micro, Regional, Large, Brewpub, Taproom | `brewery` |
| Contract, Alt Prop | `brewing_business` |
| Brewery In Planning | `planning` |
| Beer Brand | `beer_brand` |
| Location | `location` |
| Office only location | `office` |
| NonBeer, Doesn't meet Criteria | `other` |
| missing/empty (name ends with the word "household") | `household` |
| missing/empty (otherwise) or unrecognized type | `unclassified` |

Important: `brewery_type` comes from the source; `record_category` is this project's own derived label.

Household detection is defined once, as `is_household()` in `scraper/classify.py`: a name whose trailing word is "household" (case- and whitespace-insensitive). Classification and every household diagnostic use that helper, so the category and the reports cannot disagree.

### 4. Statistics (`scraper/stats.py`)

`generate_stats(breweries)` builds the summary object written to the stats file:

- Country and state counts, top-10 lists, unknown-country names.
- Missing-data counts (website, phone, latitude, longitude).
- Geographic analysis per country, including rare state codes and name/code pairs.
- Geographic anomalies: state codes shared across countries, states without codes, codes without states.
- Relationship stats: parent/child grouping, largest parent groups, parents missing from the dataset.

### 5. Export (`scraper/export.py`)

`export_json(data, filename)` writes any JSON-serializable object to disk with UTF-8 encoding and 2-space indentation, creating parent directories as needed.

### Diagnostics (optional)

`run_diagnostics(names, raw_data, breweries)` runs named investigative reports from the registry in `scraper/diagnostics.py`. Raw diagnostics receive the original source dictionaries; normalized diagnostics receive `Brewery` objects. See `docs/DIAGNOSTICS.md`.
