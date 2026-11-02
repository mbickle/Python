# Diagnostics

Diagnostics are exploratory reports for investigating data quality and source fields. They are distinct from the standard statistics generated on every run (see `generate_stats` in `scraper/stats.py`).

## Raw vs. normalized

The registry in `scraper/diagnostics.py` separates two kinds of analyses:

- **Raw diagnostics** (`RAW_DIAGNOSTICS`): receive original source dictionaries, exactly as returned by `fetch_url()`. Use these to inspect source fields, Salesforce values, and raw data quirks.
- **Normalized diagnostics** (`NORMALIZED_DIAGNOSTICS`): receive `Brewery` objects from `normalize_breweries()`. Use these to inspect the cleaned, classified dataset.

Household matching uses `is_household()` from `scraper/classify.py`, the same helper that assigns `record_category`, so reports and categories agree on which records are households.

### Running against an existing export

With `--input PATH`, only normalized diagnostics are available. A saved brewery export contains no raw source dictionaries, so raw reports and `all` are rejected with an error; run normalized reports by name instead.

## Available reports

Run `python main.py --list-diagnostics` for the authoritative list. Current reports include:

| Name | Kind | What it inspects |
| --- | --- | --- |
| `parent-relationships` | raw | Parent references in raw records |
| `raw-record-types` | raw | Source classification, membership, and flag values |
| `unknown-brewery-types` | raw | Raw records without a brewery type |
| `unknown-types-by-country` | raw | Missing types and address coverage by country |
| `parent-coverage` | normalized | Parent/child coverage in normalized records |
| `household-records` | normalized | Records whose names end with the word "household" |
| `us-unknown-types` | normalized | US records with no normalized brewery type |
| `us-region-issues` | normalized | US records with missing region information |

## Adding a diagnostic

1. Write a function that accepts the appropriate dataset (raw dicts or `Brewery` objects) and returns JSON-serializable results.
2. Register it in `RAW_DIAGNOSTICS` or `NORMALIZED_DIAGNOSTICS` under a short kebab-case name.
3. Verify the name appears with `python main.py --list-diagnostics`.
4. Run it with `python main.py --diagnostics your-report-name`.

## Conventions

- Avoid printing from diagnostic functions; returning structured data keeps reports reusable for JSON export and later analysis.
- For `Counter` or tuple-keyed results, convert them into JSON-compatible dictionaries or lists before returning — `export_json` will fail on non-serializable keys.
- Keep each diagnostic focused on one question; add a new report rather than growing an existing one.
