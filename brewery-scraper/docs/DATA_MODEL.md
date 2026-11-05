# Data model and output formats

## The `Brewery` model (`scraper/models.py`)

A pydantic model with consistent field names, regardless of what the source calls them:

| Field | Description |
| --- | --- |
| `id` | Source record ID (required) |
| `name` | Brewery name |
| `brewery_type` | Type as given by the source (e.g. `Micro`, `Brewpub`) |
| `record_category` | Derived category assigned by `classify_brewery` (see below) |
| `is_craft_brewery` | Source's craft designation flag (`Is_Craft_Brewery__c`): `true`, `false`, or `null` when absent or not a boolean |
| `street`, `city`, `state`, `state_code`, `postal_code` | Address fields |
| `country`, `country_code` | Country name and ISO alpha-2 code |
| `latitude`, `longitude` | Coordinates when present in the source |
| `website`, `phone`, `phone_normalized` | Contact info; `phone_normalized` is E.164 when parseable |
| `parent_id`, `parent_name` | Parent organization from the source account hierarchy |

## Classification

`record_category` is derived from the source's `brewery_type` by the rules in `scraper/classify.py`. Full mapping: `docs/PIPELINE.md`.

**Important distinctions:**

- `brewery_type` comes from the source; `record_category` is assigned by this project.
- A record categorized as `location` may be associated with a parent organization, but that does not establish independent brewing activity.
- A parent relationship reflects the source's account hierarchy; it is not necessarily proof of legal ownership.
- `is_craft_brewery` is the source's craft designation, populated for non-members too; treat it as a claim carried by the source, not as membership. The source's membership fields (`Membership_Record_*`, `Voting_Member__c`, `Account_Badges__c`) are deliberately not modeled.
- `source` and `source_url` are `null` when the data came from `--raw-input`, since the snapshot's origin is unknown.
- `id` is unique in normalized output. When the source repeats an ID, the first valid record wins and later duplicates are skipped, so `normalized_count` can be lower than `count`.
- Output files are gitignored local artifacts. A fresh clone has none until the first run downloads the source.
- Missing brewery types and incomplete addresses occur in the source. An `unclassified` record should not automatically be discarded.

## Output files

All three JSON output files include the same run metadata:

```json
{
  "generated_at": "2026-10-31T22:00:00+00:00",
  "source": "Brewers Association",
  "source_url": "https://www.brewersassociation.org/wp-content/themes/ba2019/json-store/breweries/breweries.json",
  "raw_source": "data/raw/breweries.json",
  "raw_fetched_at": "2026-10-31T21:58:00+00:00",
  "schema_version": "1.0",
  "normalization_version": "1.0",
  "count": 20631,
  "normalized_count": 20631
}
```

The timestamp and counts above are illustrative. `count` is the number of fetched source records; `normalized_count` is the number of normalized records exported. It can be lower than `count` because malformed records and repeated IDs are skipped.

- The brewery file adds a `breweries` array containing normalized model fields.
- The statistics file adds a `stats` object (see `generate_stats` in `scraper/stats.py`).
- The diagnostics file adds a `diagnostics` object keyed by the selected report names. It is only written when `--diagnostics` is supplied.

## Database artifacts

`scraper/db_export.py` builds two read-only sinks from the same normalized snapshot. They use the same column order and metadata encoding, but have different storage types.

### `breweries` table

The table contains one row per normalized `Brewery`, with columns named exactly as the JSON fields. `id` is the primary key and `name` is required; every other field is nullable.

| Field group | SQLite | PostgreSQL |
| --- | --- | --- |
| IDs and names (`id`, `name`, `parent_id`, `parent_name`) | `TEXT` | `TEXT` |
| Address (`brewery_type`, `street`, `city`, `state`, `state_code`, `postal_code`, `country`, `country_code`) | `TEXT` | `TEXT` |
| Contact (`website`, `phone`, `phone_normalized`) | `TEXT` | `TEXT` |
| Coordinates (`latitude`, `longitude`) | `REAL` | `DOUBLE PRECISION` |
| Classification (`record_category`, `is_craft_brewery`) | `TEXT`, `INTEGER` (`0`/`1`) | `TEXT`, `BOOLEAN` |

Indexes ship on `(latitude, longitude)`, `name`, and `(city, state)`. Records without coordinates still exist in the table but are excluded from nearby queries.

### `metadata` table

`metadata` is a key/value table. Values are JSON-encoded strings, so a consumer can decode `generated_at`, `count`, `normalized_count`, `schema_version`, and the other run metadata without losing number, boolean, or null types.

The SQLite artifact is written to a temporary file and atomically moved into place. The PostgreSQL exporter creates the read-only tables if needed, stages rows in a temporary table, and replaces the live rows in one transaction. Future writable tables and their migrations belong to the API, not this exporter.
