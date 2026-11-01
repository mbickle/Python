
import pytest


@pytest.fixture
def raw_brewery():
    def _create(
        name="Test Brewing",
        brewery_type="Micro",
        country="United States",
        state_code="WA",
        city="Seattle",
        parent=None,
        craft=True,
    ):
        return {
            "Id": "test-001",
            "Name": name,
            "Brewery_Type__c": brewery_type,
            "BillingAddress": {
                "country": country,
                "stateCode": state_code,
                "city": city,
            },
            "Parent": parent,
            "Is_Craft_Brewery__c": craft,
        }

    return _create
