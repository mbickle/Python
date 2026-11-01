from scraper.models import Brewery
from scraper.normalize import normalize_breweries


def test_normalize_returns_brewery_objects():
    raw_data = [
        {
            "Id": "001",
            "Name": "Test Brewing",
            "Brewery_Type__c": "Micro",
            "BillingAddress": {
                "city": "Seattle",
                "state": "Washington",
                "stateCode": "WA",
                "country": "United States",
                "countryCode": "US",
                "postalCode": "98101",
            },
        }
    ]

    result = normalize_breweries(raw_data)

    assert len(result) == 1
    assert isinstance(result[0], Brewery)

    brewery = result[0]

    assert brewery.id == "001"
    assert brewery.name == "Test Brewing"
    assert brewery.brewery_type == "Micro"
    assert brewery.city == "Seattle"
    assert brewery.state_code == "WA"
    assert brewery.record_category == "brewery"


def test_normalize_multiple_records():
    raw_data = [
        {
            "Id": "001",
            "Name": "First Brewing",
            "Brewery_Type__c": "Micro",
        },
        {
            "Id": "002",
            "Name": "Second Brewing",
            "Brewery_Type__c": "Brewpub",
        },
    ]

    result = normalize_breweries(raw_data)

    assert len(result) == 2
    assert result[0].name == "First Brewing"
    assert result[1].name == "Second Brewing"


def test_normalize_missing_optional_fields():
    raw_data = [
        {
            "Id": "001",
            "Name": "Minimal Brewing",
        }
    ]

    result = normalize_breweries(raw_data)

    assert len(result) == 1

    brewery = result[0]

    assert brewery.name == "Minimal Brewing"
    assert brewery.brewery_type is None
    assert brewery.record_category == "unclassified"


def test_normalize_parent_relationship():
    raw_data = [
        {
            "Id": "child-001",
            "Name": "Child Brewing",
            "Brewery_Type__c": "Micro",
            "Parent": {
                "Id": "parent-001",
                "Name": "Parent Brewing",
            },
        }
    ]

    result = normalize_breweries(raw_data)

    brewery = result[0]

    assert brewery.parent_id == "parent-001"
    assert brewery.parent_name == "Parent Brewing"
