"""Exploratory reports for the Brewers Association brewery dataset.

Raw diagnostics accept Salesforce JSON record dictionaries. Normalized
reports accept Brewery objects produced by normalize_breweries(). Helper
functions support composite reports and may use intermediate dictionaries.

Use the diagnostic registries at the bottom of this module to expose a
report through the CLI. The runner returns results for JSON export rather
than writing files or printing them itself.
"""

from collections import Counter, defaultdict

from scraper.classify import is_household
from scraper.normalize import get_country_code


def analyze_parent_relationships(raw_data):
    """Inspect parent references in the raw Salesforce records.

    Args:
        raw_data: Salesforce record dictionaries from the source feed.

    Returns:
        Counts of records with and without a non-null Parent field,
        plus up to 20 examples with their original Parent objects.

    Note:
        This checks whether Parent is non-null; it does not verify
        that the referenced parent exists in the downloaded dataset."""
    with_parent = []
    without_parent = 0

    for item in raw_data:
        parent = item.get("Parent")

        if parent is None:
            without_parent += 1
        else:
            with_parent.append({
                "name": item.get("Name"),
                "brewery_type": item.get("Brewery_Type__c"),
                "parent": parent
            })

    return {
        "total": len(raw_data),
        "with_parent": len(with_parent),
        "without_parent": without_parent,
        "examples": with_parent[:20]
    }

def analyze_unknown_types_by_country(raw_data):
    """Summarize missing brewery types and address coverage by country.

    Args:
        raw_data: Salesforce record dictionaries from the source feed.

    Returns:
        A list of per-country summaries sorted by descending count of
        missing brewery types. Each summary includes record counts,
        missing-type percentage, and city/region-code coverage.

    Note:
        Country names are mapped with get_country_code(); values that
        cannot be mapped are grouped under UNKNOWN."""
    results = defaultdict(Counter)

    for item in raw_data:
        address = item.get("BillingAddress") or {}
        country_name = address.get("country")

        country_code = get_country_code(country_name) or "UNKNOWN"

        brewery_type = item.get("Brewery_Type__c")

        results[country_code]["total"] += 1

        if not brewery_type:
            results[country_code]["unknown_type"] += 1

        if address.get("country"):
            results[country_code]["has_country"] += 1

        if address.get("city"):
            results[country_code]["has_city"] += 1

        if address.get("stateCode"):
            results[country_code]["has_region_code"] += 1

    report = []

    for country, counts in results.items():
        total = counts["total"]
        unknown = counts["unknown_type"]

        report.append({
            "country": country,
            "total": total,
            "unknown_type": unknown,
            "unknown_pct": round(unknown / total * 100, 1),
            "has_city": counts["has_city"],
            "has_region_code": counts["has_region_code"]
        })

    return sorted(
        report,
        key=lambda x: x["unknown_type"],
        reverse=True
    )

def analyze_unknown_brewery_types(raw_data):
    """Investigate raw records without a brewery type.

    Args:
        raw_data: Salesforce record dictionaries from the source feed.

    Returns:
        Counts of missing-type records, household-name matches,
        address and website presence, craft-flag values, and up to
        30 examples whose names do not match is_household().

    Note:
        Household detection uses is_household(), a trailing-word
        match, not a verified classification of the organization."""
    unknown = [
        item for item in raw_data
        if not item.get("Brewery_Type__c")
    ]

    household_count = 0
    with_address = 0
    with_website = 0
    craft_flags = Counter()

    non_household_examples = []

    for item in unknown:
        name = item.get("Name") or ""

        if is_household(name):
            household_count += 1
        elif len(non_household_examples) < 30:
            non_household_examples.append({
                "name": name,
                "craft": item.get("Is_Craft_Brewery__c"),
                "address_present": bool(item.get("BillingAddress")),
                "website_present": bool(item.get("Website"))
            })

        if item.get("BillingAddress"):
            with_address += 1

        if item.get("Website"):
            with_website += 1

        craft_flags[str(item.get("Is_Craft_Brewery__c"))] += 1

    return {
        "total_unknown": len(unknown),
        "household": household_count,
        "non_household": len(unknown) - household_count,
        "with_address": with_address,
        "with_website": with_website,
        "craft_flags": dict(craft_flags),
        "non_household_examples": non_household_examples
    }

def analyze_raw_record_types(raw_data):
    """Count source classification, membership, and flag values.

    Args:
        raw_data: Salesforce record dictionaries from the source feed.

    Returns:
        Frequency tables for Brewery_Type__c, Is_Craft_Brewery__c,
        Voting_Member__c, and Membership_Record_Status__c.

    Note:
        Missing brewery types and membership statuses use UNKNOWN;
        craft and voting flags are converted to strings, including None."""
    brewery_types = Counter()
    craft_flags = Counter()
    voting_flags = Counter()
    membership_statuses = Counter()

    for item in raw_data:
        brewery_types[
            item.get("Brewery_Type__c") or "UNKNOWN"
        ] += 1

        craft_flags[
            str(item.get("Is_Craft_Brewery__c"))
        ] += 1

        voting_flags[
            str(item.get("Voting_Member__c"))
        ] += 1

        membership_statuses[
            item.get("Membership_Record_Status__c") or "UNKNOWN"
        ] += 1

    return {
        "brewery_types": dict(brewery_types.most_common()),
        "craft_flags": dict(craft_flags),
        "voting_flags": dict(voting_flags),
        "membership_statuses": dict(membership_statuses)
    }

def analyze_parent_coverage(breweries):
    """
    Measure how many parent references resolve within the dataset.

    Salesforce Account records can reference another Account
    through their Parent field.

    This diagnostic determines:
      - How many records reference a parent.
      - How many parent IDs exist in the current dataset.
      - How many parent IDs cannot be resolved.
      - Examples of unresolved parent references.

    Args:
        breweries: List of normalized Brewery objects.

    Returns:
        Dictionary containing relationship coverage counts
        and up to 20 unresolved parent examples.

    Note:
        A missing parent does not necessarily indicate bad data.
        The referenced Salesforce Account may simply be absent
        from the published dataset.
    """
    brewery_ids = {
        b.id for b in breweries if b.id
    }

    with_parent = 0
    parent_found = 0
    parent_missing = 0

    missing_examples = []

    for b in breweries:
        if not b.parent_id:
            continue

        with_parent += 1

        if b.parent_id in brewery_ids:
            parent_found += 1
        else:
            parent_missing += 1

            if len(missing_examples) < 20:
                missing_examples.append({
                    "child": b.name,
                    "parent": b.parent_name,
                    "parent_id": b.parent_id
                })

    return {
        "with_parent": with_parent,
        "parent_found_in_dataset": parent_found,
        "parent_missing_from_dataset": parent_missing,
        "missing_examples": missing_examples
    }

def analyze_us_unknown_types(breweries):
    """Identify US records with no normalized brewery type.

    Args:
        breweries: Normalized Brewery objects.

    Returns:
        Total missing-type US records, household-name match count,
        and details of all other matching US records."""
    records = [
        b for b in breweries
        if b.country_code == "US"
        and not b.brewery_type
    ]

    households = [
        b for b in records
        if is_household(b.name)
    ]

    others = [
        b for b in records
        if not is_household(b.name)
    ]

    return {
        "total_unknown": len(records),
        "households": len(households),
        "other_records": [
            {
                "name": b.name,
                "city": b.city,
                "state": b.state,
                "brewery_type": b.brewery_type
            }
            for b in others
        ]
    }

def analyze_household_records(breweries):
    """Summarize normalized records whose names end with 'household'.

    Args:
        breweries: Normalized Brewery objects.

    Returns:
        Household-name match count, breakdowns by country and brewery
        type, and counts with or without a state name or code.

    Note:
        is_household() owns the name match, which ignores case and
        whitespace; it does not depend on record_category."""
    total_households = 0

    households_by_country = Counter()
    households_by_type = Counter()

    with_region = 0
    without_region = 0

    for b in breweries:
        household = is_household(b.name)

        if not household:
            continue

        total_households += 1

        country = b.country_code or "UNKNOWN"
        brewery_type = b.brewery_type or "UNKNOWN"

        households_by_country[country] += 1
        households_by_type[brewery_type] += 1

        if b.state_code or b.state:
            with_region += 1
        else:
            without_region += 1

    return {
        "total_households": total_households,
        "households_by_country": dict(households_by_country.most_common()),
        "households_by_type": dict(households_by_type.most_common()),
        "with_region": with_region,
        "without_region": without_region
    }

def analyze_household_types(missing):
    """Group missing-region record dictionaries by household name and type.

    Args:
        missing: Dictionaries with name and brewery_type keys, such as
            those from get_us_breweries_missing_region().

    Returns:
        A defaultdict of Counters keyed by Household or Other, with
        counts for each brewery type (or UNKNOWN when absent)."""
    results = defaultdict(Counter)

    for b in missing:
        household = is_household(b["name"])
        brewery_type = b["brewery_type"] or "UNKNOWN"

        category = (
            "Household"
            if household
            else "Other"
        )

        results[category][brewery_type] += 1

    return results

def analyze_missing_brewery_types(missing):
    """Count brewery types in a collection of record dictionaries.

    Args:
        missing: Dictionaries containing a brewery_type key, typically
            returned by get_us_breweries_missing_region().

    Returns:
        Counter mapping brewery type (or UNKNOWN) to record count."""
    return Counter(
        b["brewery_type"] or "UNKNOWN"
        for b in missing
    )

def analyze_us_missing_region(missing):
    """Categorize missing-region records using their names.

    Args:
        missing: Dictionaries with a name key, typically returned by
            get_us_breweries_missing_region().

    Returns:
        Counter of Household, Homebrew, Club, and Other matches.

    Note:
        Categories are checked in that order; each record is counted
        once under the first matching case-insensitive name pattern."""
    name_patterns = Counter()

    for b in missing:
        name = (b["name"] or "").lower()

        if is_household(b["name"]):
            name_patterns["Household"] += 1
        elif "homebrew" in name:
            name_patterns["Homebrew"] += 1
        elif "club" in name:
            name_patterns["Club"] += 1
        else:
            name_patterns["Other"] += 1

    return name_patterns

def analyze_us_region_issues(breweries):
    """
    Investigate US records with missing or inconsistent regions.

    Combines several existing helper functions into one
    JSON-serializable report suitable for the CLI.

    Args:
        breweries: List of normalized Brewery objects.

    Returns:
        Summary of missing-region records, their brewery
        types, name patterns, and state name/code pairs.
    """
    missing = get_us_breweries_missing_region(breweries)

    # The existing helpers return Counter/defaultdict values.
    # Convert them to ordinary dictionaries for JSON export.
    name_patterns = analyze_us_missing_region(missing)
    brewery_types = analyze_missing_brewery_types(missing)
    household_types = analyze_household_types(missing)
    region_pairs = get_us_region_pairs(breweries)

    return {
        "missing_region_count": len(missing),
        "name_patterns": dict(name_patterns),
        "brewery_types": dict(brewery_types),
        "household_types": {
            category: dict(counts)
            for category, counts in household_types.items()
        },
        "region_pairs": [
            {
                "state_code": code,
                "state_name": name,
                "count": count
            }
            for (code, name), count in region_pairs.most_common()
        ],
        "missing_examples": missing[:30]
    }

def get_us_breweries_missing_region(breweries):
    """Collect US breweries with neither a state code nor a state name.

    Args:
        breweries: Normalized Brewery objects.

    Returns:
        A list of dictionaries containing name, location, and brewery
        type fields for US records missing both region fields.

    Note:
        The country-code comparison is normalized to uppercase;
        a blank or missing country code is not considered US."""
    missing = []

    for b in breweries:
        country_code = (b.country_code or "").strip().upper()

        if country_code != "US":
            continue

        if not b.state_code and not b.state:
            missing.append({
                "name": b.name,
                "city": b.city,
                "state": b.state,
                "state_code": b.state_code,
                "postal_code": b.postal_code,
                "street": b.street,
                "brewery_type": b.brewery_type,
            })

    return missing

def get_us_region_pairs(breweries):
    """Count observed state-code/state-name combinations for US records.

    Args:
        breweries: Normalized Brewery objects.

    Returns:
        Counter keyed by (state_code, state_name) tuples. Missing
        components of otherwise present pairs are labeled MISSING.

    Note:
        Records missing both state code and name are excluded.
        Tuple keys require conversion before JSON serialization."""
    region_pairs = Counter()

    for b in breweries:
        country_code = (b.country_code or "").strip().upper()

        if country_code != "US":
            continue

        region_code = (b.state_code or "").strip().upper()
        region_name = (b.state or "").strip()

        if region_code or region_name:
            region_pairs[(region_code or "MISSING", region_name or "MISSING")] += 1

    return region_pairs


def _iter_fields(item, prefix=""):
    """Yield (dotted field name, value) pairs, flattening nested objects."""
    for key, value in item.items():
        name = f"{prefix}{key}"

        if isinstance(value, dict):
            yield from _iter_fields(value, prefix=f"{name}.")
        else:
            yield name, value


def analyze_source_fields(raw_data):
    """Inventory the fields present in the raw source records.

    Args:
        raw_data: Salesforce record dictionaries from the source feed.

    Returns:
        Total record count plus one entry per field, sorted by how many
        records contain it: presence count and percentage, inferred
        value types, and up to three example values.

    Note:
        Nested objects are flattened into dotted names
        (BillingAddress.city, Parent.Name). Arrays are reported as
        values rather than walked. A field that is always null still
        appears, with NoneType among its types.
    """
    presence = Counter()
    value_types = defaultdict(set)
    examples = defaultdict(list)

    for item in raw_data:
        for field, value in _iter_fields(item):
            presence[field] += 1
            value_types[field].add(type(value).__name__)

            if value is None:
                continue

            if value not in examples[field] and len(examples[field]) < 3:
                examples[field].append(value)

    total = len(raw_data)

    return {
        "total_records": total,
        "field_count": len(presence),
        "fields": [
            {
                "field": field,
                "present": count,
                "present_pct": round(count / total * 100, 1) if total else 0.0,
                "types": sorted(value_types[field]),
                "examples": examples[field],
            }
            for field, count in presence.most_common()
        ],
    }


# ------------------------------------------------------------
# Diagnostic registry
# ------------------------------------------------------------
# Each entry maps a command-line name to an analysis function.
#
# We maintain separate registries because some diagnostics
# operate on raw Salesforce dictionaries, while others need
# normalized Brewery objects.
#
# Example:
#   python main.py --diagnostics parent-coverage
#   python main.py --diagnostics raw-record-types
#   python main.py --diagnostics all
# ------------------------------------------------------------

RAW_DIAGNOSTICS = {
    "source-fields": analyze_source_fields,
    "parent-relationships": analyze_parent_relationships,
    "raw-record-types": analyze_raw_record_types,
    "unknown-brewery-types": analyze_unknown_brewery_types,
    "unknown-types-by-country": analyze_unknown_types_by_country,
}

NORMALIZED_DIAGNOSTICS = {
    "parent-coverage": analyze_parent_coverage,
    "household-records": analyze_household_records,
    "us-unknown-types": analyze_us_unknown_types,
    "us-region-issues": analyze_us_region_issues,
}

def available_diagnostics():
    """
    Return the names of all available diagnostic reports.

    Used by the CLI to implement --list-diagnostics and
    validate the names supplied to --diagnostics.
    """
    return sorted(
        set(RAW_DIAGNOSTICS) | set(NORMALIZED_DIAGNOSTICS)
    )

def run_diagnostics(names, raw_data, breweries):
    """
    Execute selected diagnostics and return their results.

    Args:
        names:
            List of diagnostic names, or ['all'].

        raw_data:
            Original Salesforce records returned by fetch_url().

        breweries:
            Normalized Brewery objects.

    Returns:
        Dictionary mapping diagnostic names to their results.

    Example:
        {
            "parent-coverage": {...},
            "household-records": {...}
        }
    """
    if "all" in names:
        names = available_diagnostics()

    results = {}

    for name in names:

        # Select the correct function and data representation.
        if name in RAW_DIAGNOSTICS:
            diagnostic = RAW_DIAGNOSTICS[name]
            result = diagnostic(raw_data)

        elif name in NORMALIZED_DIAGNOSTICS:
            diagnostic = NORMALIZED_DIAGNOSTICS[name]
            result = diagnostic(breweries)

        else:
            raise ValueError(f"Unknown diagnostic: {name}")

        # Store the result instead of printing it.
        results[name] = result

    return results
