
def classify_brewery(brewery):
    name = (brewery.name or "").strip().casefold()
    brewery_type = brewery.brewery_type

    if not brewery_type:
        if name.endswith(" household"):
            return "household"
        return "unclassified"

    categories = {
        "Micro": "brewery",
        "Regional": "brewery",
        "Large": "brewery",
        "Brewpub": "brewery",
        "Taproom": "brewery",
        "Contract": "brewing_business",
        "Alt Prop": "brewing_business",
        "Brewery In Planning": "planning",
        "Beer Brand": "beer_brand",
        "Location": "location",
        "Office only location": "office",
        "NonBeer": "other",
        "Doesn't meet Criteria": "other",
    }



    return categories.get(brewery_type, "unclassified")