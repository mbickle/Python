import json

from scraper.models import Brewery


def parse_breweries(raw: str):
    try:
        data = json.loads(raw)
        breweries = [Brewery(**item) for item in data]
        return breweries
    except Exception:
        # If it's not JSON, return empty list for now
        return []