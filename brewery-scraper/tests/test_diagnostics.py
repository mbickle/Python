from scraper.diagnostics import (
    analyze_household_records,
    analyze_parent_coverage,
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
