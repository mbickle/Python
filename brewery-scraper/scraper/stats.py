from collections import Counter, defaultdict


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

def generate_stats(breweries):

    total = len(breweries)

    country_counts = Counter()
    country_brewery_counts = Counter()
    state_counts = Counter()

    country_names_without_codes = Counter()
    state_names_without_codes = Counter()

    # Geographic information grouped by country
    states_by_country = defaultdict(Counter)
    countries_by_state = defaultdict(set)

    # Missing geographic information, grouped by country
    missing_region_name_by_country = Counter()
    missing_region_code_by_country = Counter()
    missing_both_regions_by_country = Counter()

    # Track state/region name and code combinations
    region_pairs_by_country = defaultdict(Counter)

    # Examples to help investigate inconsistent records
    state_without_code = []
    code_without_state = []

    for b in breweries:

        country_code = (b.country_code or "").strip().upper() or "UNKNOWN"
        country_name = (b.country or "").strip() or "UNKNOWN"

        state_code = (b.state_code or "").strip().upper() or None
        state_name = (b.state or "").strip() or None

        # Country counts
        if country_code != "UNKNOWN":
            country_counts[country_code] += 1

        country_brewery_counts[country_code] += 1

        if country_code == "UNKNOWN":
            country_names_without_codes[country_name] += 1

        # Region/state counts
        if state_code:
            state_counts[state_code] += 1
            states_by_country[country_code][state_code] += 1

            # Only compare codes across known countries
            if country_code != "UNKNOWN":
                countries_by_state[state_code].add(country_code)

        # Missing region information
        if not state_name:
            missing_region_name_by_country[country_code] += 1

        if not state_code:
            missing_region_code_by_country[country_code] += 1

        if not state_name and not state_code:
            missing_both_regions_by_country[country_code] += 1

        # A name exists, but its code is missing
        if state_name and not state_code:
            state_names_without_codes[state_name] += 1

            if len(state_without_code) < 20:
                state_without_code.append({
                    "country": country_name,
                    "brewery": b.name,
                    "state": state_name
                })

        # A code exists, but its name is missing
        if state_code and not state_name and len(code_without_state) < 20:
            code_without_state.append({
                "country": country_name,
                "brewery": b.name,
                "state_code": state_code
            })

        # Track the actual name/code combination
        if state_name or state_code:
            region_pairs_by_country[country_code][
                (state_code or "NO_CODE", state_name or "NO_NAME")
            ] += 1

    # Geographic analysis grouped by country
    geographic_analysis = {}

    for country in sorted(country_brewery_counts):

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
                "breweries": count
            }
            for (code, name), count in
            region_pairs_by_country[country].most_common()
        ]

        geographic_analysis[country] = {
            "total_breweries": country_brewery_counts[country],
            "breweries_with_state_code": sum(states.values()),
            "missing_region_name": missing_region_name_by_country[country],
            "missing_region_code": missing_region_code_by_country[country],
            "missing_both_region_fields": missing_both_regions_by_country[country],
            "unique_states": len(states),
            "states": dict(states.most_common()),
            "rare_state_codes": rare_codes,
            "region_name_code_pairs": region_pairs
        }

    # Codes used in more than one known country
    shared_state_codes = {
        code: sorted(countries)
        for code, countries in countries_by_state.items()
        if len(countries) > 1
    }

    return {
        "total_breweries": total,

        # Unique known country and region codes
        "countries": len(country_counts),
        "states": len(state_counts),

        "top_countries": dict(
            country_counts.most_common(10)
        ),

        "top_states": dict(
            state_counts.most_common(10)
        ),

        "unknown_countries": dict(
            country_names_without_codes.most_common(20)
        ),

        "state_names_without_codes": dict(
            state_names_without_codes.most_common(20)
        ),

        "missing_data": {
            "website": sum(1 for b in breweries if not b.website),
            "phone": sum(1 for b in breweries if not b.phone),
            "latitude": sum(1 for b in breweries if b.latitude is None),
            "longitude": sum(1 for b in breweries if b.longitude is None)
        },

        "geographic_analysis": geographic_analysis,

        "geographic_anomalies": {
            "shared_state_codes": shared_state_codes,
            "state_without_code": state_without_code,
            "code_without_state": code_without_state
        },

        "relationships": calculate_relationship_stats(breweries)
    }