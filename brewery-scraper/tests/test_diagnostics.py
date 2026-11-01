from scraper.diagnostics import (
    analyze_household_records,
    analyze_household_types,
    analyze_parent_coverage,
    analyze_parent_relationships,
    analyze_raw_record_types,
    analyze_unknown_brewery_types,
    analyze_unknown_types_by_country,
    analyze_us_unknown_types,
    available_diagnostics,
    run_diagnostics,
)
from scraper.models import Brewery


def test_parent_coverage():
    breweries = [
        Brewery(
            id="parent-001",
            name="Parent Brewing"
        ),
        Brewery(
            id="child-001",
            name="Child Brewing",
            parent_id="parent-001"
        ),
        Brewery(
            id="child-002",
            name="Orphan Brewing",
            parent_id="missing-parent",
            parent_name="Missing Parent"
        ),
    ]

    result = analyze_parent_coverage(breweries)

    assert result["with_parent"] == 2
    assert result["parent_found_in_dataset"] == 1
    assert result["parent_missing_from_dataset"] == 1
    assert len(result["missing_examples"]) == 1
    assert result["missing_examples"][0]["child"] == "Orphan Brewing"


def test_household_records():
    breweries = [
        Brewery(
            id="001",
            name="Smith Household",
            country_code="US",
            state_code="WA"
        ),
        Brewery(
            id="002",
            name="Jones Household",
            country_code="US"
        ),
        Brewery(
            id="003",
            name="Actual Brewing Company",
            country_code="US"
        ),
    ]

    result = analyze_household_records(breweries)

    assert result["total_households"] == 2
    assert result["households_by_country"]["US"] == 2
    assert result["with_region"] == 1
    assert result["without_region"] == 1


def test_us_unknown_types():
    breweries = [
        Brewery(
            id="001",
            name="Smith Household",
            country_code="US"
        ),
        Brewery(
            id="002",
            name="Unknown Brewing",
            country_code="US"
        ),
        Brewery(
            id="003",
            name="Foreign Brewing",
            country_code="CA"
        ),
        Brewery(
            id="004",
            name="Known Brewing",
            country_code="US",
            brewery_type="Micro"
        ),
    ]

    result = analyze_us_unknown_types(breweries)

    assert result["total_unknown"] == 2
    assert result["households"] == 1
    assert len(result["other_records"]) == 1
    assert result["other_records"][0]["name"] == "Unknown Brewing"


def test_diagnostic_registry():
    available = available_diagnostics()

    assert "parent-coverage" in available
    assert "household-records" in available
    assert "raw-record-types" in available


def test_run_selected_diagnostic():
    breweries = [
        Brewery(id="001", name="Parent Brewing"),
        Brewery(
            id="002",
            name="Child Brewing",
            parent_id="001"
        ),
    ]

    result = run_diagnostics(
        ["parent-coverage"],
        raw_data=[],
        breweries=breweries,
    )

    assert "parent-coverage" in result
    assert "household-records" not in result

    coverage = result["parent-coverage"]

    assert coverage["with_parent"] == 1
    assert coverage["parent_found_in_dataset"] == 1

def test_parent_relationships(raw_brewery):
    raw_data = [
        raw_brewery(name="Independent Brewing"),
        raw_brewery(
            name="Subsidiary Brewing",
            parent={
                "Id": "parent-001",
                "Name": "Parent Brewing",
            },
        ),
    ]

    result = analyze_parent_relationships(raw_data)

    assert result["total"] == 2
    assert result["with_parent"] == 1
    assert result["without_parent"] == 1
    assert result["examples"][0]["name"] == "Subsidiary Brewing"
    assert result["examples"][0]["parent"]["Id"] == "parent-001"

def test_raw_record_types(raw_brewery):
    raw_data = [
        raw_brewery(brewery_type="Micro", craft=True),
        raw_brewery(brewery_type="Micro", craft=False),
        raw_brewery(brewery_type="Brewpub", craft=True),
        raw_brewery(brewery_type=None, craft=None),
    ]

    result = analyze_raw_record_types(raw_data)

    assert result["brewery_types"] == {
        "Micro": 2,
        "Brewpub": 1,
        "UNKNOWN": 1,
    }

    assert result["craft_flags"] == {
        "True": 2,
        "False": 1,
        "None": 1,
    }

def test_unknown_brewery_types(raw_brewery):
    raw_data = [
        raw_brewery(
            name="Smith Household",
            brewery_type=None,
        ),
        raw_brewery(
            name="Mystery Brewing",
            brewery_type=None,
        ),
        raw_brewery(
            name="Known Brewing",
            brewery_type="Micro",
        ),
    ]

    result = analyze_unknown_brewery_types(raw_data)

    assert result["total_unknown"] == 2
    assert result["household"] == 1
    assert result["non_household"] == 1
    assert result["with_address"] == 2
    assert len(result["non_household_examples"]) == 1
    assert result["non_household_examples"][0]["name"] == "Mystery Brewing"

def test_unknown_types_by_country(raw_brewery):
    raw_data = [
        raw_brewery(
            name="Washington Brewing",
            country="United States",
            brewery_type="Micro",
        ),
        raw_brewery(
            name="Unknown US Brewing",
            country="United States",
            brewery_type=None,
        ),
        raw_brewery(
            name="Another Unknown US Brewing",
            country="United States",
            brewery_type=None,
        ),
        raw_brewery(
            name="Canadian Brewing",
            country="Canada",
            brewery_type="Micro",
        ),
        raw_brewery(
            name="Unknown Canadian Brewing",
            country="Canada",
            brewery_type=None,
        ),
    ]

    results = analyze_unknown_types_by_country(raw_data)

    assert len(results) == 2
    
    # Convert the list into a dictionary keyed by country.
    by_country = {
        item["country"]: item
        for item in results
    }

    # United States
    us = by_country["US"]

    assert us["total"] == 3
    assert us["unknown_type"] == 2
    assert us["unknown_pct"] == 66.7
    assert us["has_city"] == 3
    assert us["has_region_code"] == 3

    # Canada
    ca = by_country["CA"]

    assert ca["total"] == 2
    assert ca["unknown_type"] == 1
    assert ca["unknown_pct"] == 50.0
    assert ca["has_city"] == 2
    assert ca["has_region_code"] == 2

def test_unknown_types_by_country_missing_country(raw_brewery):
    raw_data = [
        raw_brewery(
            name="Mystery Brewing",
            country=None,
            brewery_type=None,
            city=None,
            state_code=None,
        ),
    ]

    results = analyze_unknown_types_by_country(raw_data)

    assert len(results) == 1

    result = results[0]

    assert result["country"] == "UNKNOWN"
    assert result["total"] == 1
    assert result["unknown_type"] == 1
    assert result["unknown_pct"] == 100.0
    assert result["has_city"] == 0
    assert result["has_region_code"] == 0

def test_household_types():
    missing = [
        {"name": "Smith Household", "brewery_type": None},
        {"name": "Jones Household", "brewery_type": None},
        {"name": "Known Brewing", "brewery_type": "Micro"},
    ]

    result = analyze_household_types(missing)

    assert result["Household"]["UNKNOWN"] == 2
    assert result["Other"]["Micro"] == 1