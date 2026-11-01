import pytest

from scraper.classify import classify_brewery
from scraper.models import Brewery


@pytest.mark.parametrize(
    "brewery_type, expected_category",
    [
        ("Micro", "brewery"),
        ("Regional", "brewery"),
        ("Large", "brewery"),
        ("Brewpub", "brewery"),
        ("Taproom", "brewery"),
        ("Contract", "brewing_business"),
        ("Alt Prop", "brewing_business"),
        ("Brewery In Planning", "planning"),
        ("Beer Brand", "beer_brand"),
        ("Location", "location"),
        ("Office only location", "office"),
        ("NonBeer", "other"),
        ("Doesn't meet Criteria", "other"),
        ("Something Unexpected", "unclassified"),
    ],
)
def test_classifies_brewery_types(
    brewery_type, expected_category
):
    brewery = Brewery(
        id="test-001",
        name="Test Brewery",
        brewery_type=brewery_type,
    )

    result = classify_brewery(brewery)

    assert result == expected_category


def test_household_without_brewery_type():
    brewery = Brewery(
        id="test-002",
        name="Smith Household",
        brewery_type=None,
    )

    assert classify_brewery(brewery) == "household"


def test_missing_type_is_unclassified():
    brewery = Brewery(
        id="test-003",
        name="Mystery Brewing Company",
        brewery_type=None,
    )

    assert classify_brewery(brewery) == "unclassified"


def test_household_with_explicit_type():
    brewery = Brewery(
        id="test-004",
        name="Smith Household",
        brewery_type="Micro",
    )

    # An explicit brewery type takes precedence.
    assert classify_brewery(brewery) == "brewery"
