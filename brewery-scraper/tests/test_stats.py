import pytest

from scraper.normalize import normalize_breweries
from scraper.stats import calculate_relationship_stats, generate_stats


@pytest.fixture
def breweries():
    raw_data = [
        {
            "Id": "001",
            "Name": "Alpha Brewing",
            "Brewery_Type__c": "Micro",
            "Website": "https://alpha.example",
            "Phone": "(206) 555-0100",
            "BillingAddress": {
                "city": "Seattle",
                "state": "Washington",
                "stateCode": "WA",
                "country": "United States",
                "latitude": 47.6,
                "longitude": -122.3,
            },
        },
        {
            "Id": "002",
            "Name": "Beta Brewing",
            "Brewery_Type__c": "Brewpub",
            "BillingAddress": {
                "city": "Portland",
                "state": "Oregon",
                "stateCode": "OR",
                "country": "United States",
            },
            "Parent": {"Id": "001", "Name": "Alpha Brewing"},
        },
        {
            "Id": "003",
            "Name": "Gamma Brewing",
            "Brewery_Type__c": "Micro",
            "BillingAddress": {
                "city": "Berlin",
                "country": "Germany",
            },
            "Parent": {"Id": "999", "Name": "Ghost Parent"},
        },
    ]
    return normalize_breweries(raw_data)


def test_generate_stats_totals(breweries):
    stats = generate_stats(breweries)

    assert stats["total_breweries"] == 3
    assert stats["countries"] == 2  # US and DE
    assert stats["top_countries"] == {"US": 2, "DE": 1}


def test_generate_stats_missing_data(breweries):
    stats = generate_stats(breweries)
    missing = stats["missing_data"]

    assert missing["website"] == 2
    assert missing["phone"] == 2
    assert missing["latitude"] == 2
    assert missing["longitude"] == 2


def test_generate_stats_state_counts(breweries):
    stats = generate_stats(breweries)

    assert stats["top_states"] == {"WA": 1, "OR": 1}


def test_relationship_stats_parent_grouping(breweries):
    rel = calculate_relationship_stats(breweries)

    assert rel["total_records"] == 3
    assert rel["records_with_parent"] == 2
    assert rel["distinct_parent_ids"] == 2
    assert rel["parents_with_multiple_children"] == 0


def test_relationship_stats_missing_parent(breweries):
    rel = calculate_relationship_stats(breweries)

    assert rel["parent_records_missing"] == 1  # Ghost Parent (999)
    assert rel["parent_records_found"] == 1  # Alpha (001)

    groups = {g["parent_id"]: g for g in rel["largest_groups"]}
    assert groups["999"]["parent_in_dataset"] is False
    assert groups["999"]["parent_name"] == "Ghost Parent"
    assert groups["001"]["parent_in_dataset"] is True
    assert groups["001"]["parent_name"] == "Alpha Brewing"


def test_generate_stats_empty():
    stats = generate_stats([])

    assert stats["total_breweries"] == 0
    assert stats["top_countries"] == {}
    assert stats["relationships"]["total_records"] == 0


def test_generate_stats_geographic_edge_cases():
    raw_data = [
        {
            "Id": "010",
            "Name": "No Country Brewing",
            "Brewery_Type__c": "Micro",
            # no BillingAddress at all -> UNKNOWN country
        },
        {
            "Id": "011",
            "Name": "Name Only Brewing",
            "Brewery_Type__c": "Micro",
            "BillingAddress": {
                "city": "Austin",
                "state": "Texas",  # name but no code
                "country": "United States",
            },
        },
        {
            "Id": "012",
            "Name": "Code Only Brewing",
            "Brewery_Type__c": "Micro",
            "BillingAddress": {
                "city": "Denver",
                "stateCode": "CO",  # code but no name
                "country": "United States",
            },
        },
    ]
    breweries = normalize_breweries(raw_data)
    stats = generate_stats(breweries)

    assert stats["unknown_countries"] == {"UNKNOWN": 1}
    assert stats["state_names_without_codes"] == {"Texas": 1}

    anomalies = stats["geographic_anomalies"]
    assert anomalies["state_without_code"][0]["state"] == "Texas"
    assert anomalies["code_without_state"][0]["state_code"] == "CO"
