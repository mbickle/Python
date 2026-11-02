"""Summary statistics built from normalized brewery records.

Each section is produced by its own function so a new statistic can be
added without growing one large accumulator loop.
"""

from collections import Counter, defaultdict

UNKNOWN = "UNKNOWN"


def calculate_relationship_stats(breweries):
    # Build an index of every brewery by Salesforce ID.
    breweries_by_id = {
        brewery.id: brewery
        for brewery in breweries
    }

    # Group child records by their parent ID.
    children_by_parent = defaultdict(list)

    for brewery in breweries:
        if brewery.parent_id:
            children_by_parent[brewery.parent_id].append(brewery)

    # Count how many children each parent has.
    children_counts = Counter({
        parent_id: len(children)
        for parent_id, children in children_by_parent.items()
    })

    # Build a list of the largest parent-child groups.
    largest_groups = []

    for parent_id, count in children_counts.most_common(20):
        children = children_by_parent[parent_id]

        parent = breweries_by_id.get(parent_id)

        # Use the full parent record when available.
        # Otherwise use the name embedded in the child record.
        parent_name = (
            parent.name
            if parent
            else children[0].parent_name
        )

        largest_groups.append({
            "parent_id": parent_id,
            "parent_name": parent_name,
            "parent_in_dataset": parent is not None,
            "child_count": count,
            "children": [
                {
                    "id": child.id,
                    "name": child.name,
                    "category": child.record_category,
                    "brewery_type": child.brewery_type
                }
                for child in children
            ]
        })

    return {
        "total_records": len(breweries),
        "records_with_parent": sum(children_counts.values()),
        "distinct_parent_ids": len(children_by_parent),
        "parents_with_multiple_children": sum(
            1 for count in children_counts.values()
            if count > 1
        ),
        "parent_records_found": sum(
            len(children)
            for parent_id, children in children_by_parent.items()
            if parent_id in breweries_by_id
        ),
        "parent_records_missing": sum(
            len(children)
            for parent_id, children in children_by_parent.items()
            if parent_id not in breweries_by_id
        ),
        "largest_groups": largest_groups
    }


def _region_fields(brewery) -> tuple[str, str, str | None, str | None]:
    """Normalize the country/region fields used by the geographic reports."""
    country_code = (brewery.country_code or "").strip().upper() or UNKNOWN
    country_name = (brewery.country or "").strip() or UNKNOWN
    state_code = (brewery.state_code or "").strip().upper() or None
    state_name = (brewery.state or "").strip() or None

    return country_code, country_name, state_code, state_name


def _country_stats(breweries) -> dict:
    """Country totals, most common countries, and unmapped country names."""
    countries = Counter()
    names_without_codes = Counter()

    for brewery in breweries:
        country_code, country_name, _, _ = _region_fields(brewery)

        if country_code != UNKNOWN:
            countries[country_code] += 1
        else:
            names_without_codes[country_name] += 1

    return {
        "count": len(countries),
        "top": dict(countries.most_common(10)),
        "unknown": dict(names_without_codes.most_common(20)),
    }


def _missing_data_stats(breweries) -> dict:
    """Count records missing each optional contact or location field."""
    return {
        "website": sum(1 for b in breweries if not b.website),
        "phone": sum(1 for b in breweries if not b.phone),
        "latitude": sum(1 for b in breweries if b.latitude is None),
        "longitude": sum(1 for b in breweries if b.longitude is None),
    }


def _region_counts(breweries) -> dict:
    """Per-country counts of region coverage and missing fields."""
    state_counts = Counter()
    states_by_country = defaultdict(Counter)
    countries_by_state = defaultdict(set)

    missing_name = Counter()
    missing_code = Counter()
    missing_both = Counter()

    names_without_codes = Counter()
    totals_by_country = Counter()

    for brewery in breweries:
        country_code, _, state_code, state_name = _region_fields(brewery)

        totals_by_country[country_code] += 1

        if state_code:
            state_counts[state_code] += 1
            states_by_country[country_code][state_code] += 1

            # Only compare codes across known countries
            if country_code != UNKNOWN:
                countries_by_state[state_code].add(country_code)

        if not state_name:
            missing_name[country_code] += 1

        if not state_code:
            missing_code[country_code] += 1

        if not state_name and not state_code:
            missing_both[country_code] += 1

        if state_name and not state_code:
            names_without_codes[state_name] += 1

    return {
        "state_counts": state_counts,
        "states_by_country": states_by_country,
        "countries_by_state": countries_by_state,
        "missing_name": missing_name,
        "missing_code": missing_code,
        "missing_both": missing_both,
        "names_without_codes": names_without_codes,
        "totals_by_country": totals_by_country,
    }


def _region_observations(breweries) -> tuple[list, list, dict]:
    """Example records and name/code pair counts used by the report."""
    state_without_code = []
    code_without_state = []
    pairs_by_country = defaultdict(Counter)

    for brewery in breweries:
        country_code, country_name, state_code, state_name = _region_fields(
            brewery
        )

        # A name exists, but its code is missing
        if state_name and not state_code and len(state_without_code) < 20:
            state_without_code.append({
                "country": country_name,
                "brewery": brewery.name,
                "state": state_name,
            })

        # A code exists, but its name is missing
        if state_code and not state_name and len(code_without_state) < 20:
            code_without_state.append({
                "country": country_name,
                "brewery": brewery.name,
                "state_code": state_code,
            })

        # Track the actual name/code combination
        if state_name or state_code:
            pairs_by_country[country_code][
                (state_code or "NO_CODE", state_name or "NO_NAME")
            ] += 1

    return state_without_code, code_without_state, pairs_by_country


def _region_stats(breweries) -> dict:
    """Region totals, per-country detail, and region anomalies."""
    counts = _region_counts(breweries)

    state_without_code, code_without_state, pairs_by_country = (
        _region_observations(breweries)
    )

    states_by_country = counts["states_by_country"]
    by_country = {}

    for country in sorted(counts["totals_by_country"]):
        states = states_by_country.get(country, Counter())

        # Rare codes are more meaningful when considered within a country
        rare_codes = {
            code: count
            for code, count in states.items()
            if count <= 5
        }

        # Convert name/code combinations into JSON-friendly records
        region_pairs = [
            {
                "state_code": code,
                "state_name": name,
                "breweries": count,
            }
            for (code, name), count
            in pairs_by_country[country].most_common()
        ]

        by_country[country] = {
            "total_breweries": counts["totals_by_country"][country],
            "breweries_with_state_code": sum(states.values()),
            "missing_region_name": counts["missing_name"][country],
            "missing_region_code": counts["missing_code"][country],
            "missing_both_region_fields": counts["missing_both"][country],
            "unique_states": len(states),
            "states": dict(states.most_common()),
            "rare_state_codes": rare_codes,
            "region_name_code_pairs": region_pairs,
        }

    # Codes used in more than one known country
    shared_state_codes = {
        code: sorted(countries)
        for code, countries in counts["countries_by_state"].items()
        if len(countries) > 1
    }

    return {
        "count": len(counts["state_counts"]),
        "top": dict(counts["state_counts"].most_common(10)),
        "names_without_codes": dict(
            counts["names_without_codes"].most_common(20)
        ),
        "by_country": by_country,
        "anomalies": {
            "shared_state_codes": shared_state_codes,
            "state_without_code": state_without_code,
            "code_without_state": code_without_state,
        },
    }


def generate_stats(breweries):
    """Build the statistics object written alongside the brewery export."""
    countries = _country_stats(breweries)
    regions = _region_stats(breweries)

    return {
        "total_breweries": len(breweries),

        # Unique known country and region codes
        "countries": countries["count"],
        "states": regions["count"],

        "top_countries": countries["top"],
        "top_states": regions["top"],

        "unknown_countries": countries["unknown"],
        "state_names_without_codes": regions["names_without_codes"],

        "missing_data": _missing_data_stats(breweries),

        "geographic_analysis": regions["by_country"],
        "geographic_anomalies": regions["anomalies"],

        "relationships": calculate_relationship_stats(breweries),
    }
