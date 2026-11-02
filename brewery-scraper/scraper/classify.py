"""Derived record categories.

``record_category`` is this project's own label. It comes from the
source's ``brewery_type`` when one is present, and from the record name
only when the type is missing.

Household detection lives here so classification and the household
diagnostics share a single definition of what a household record is.
"""

import re

# Source records for individuals end with the literal word, for example
# "Smith Household". Anchoring to the trailing word keeps businesses
# that merely use the word mid-name out of the household category.
HOUSEHOLD_SUFFIX = re.compile(r"\bhousehold$")

TYPE_CATEGORIES = {
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


def is_household(name: str | None) -> bool:
    """Return True when a record name ends with the word 'household'.

    The comparison ignores case and surrounding whitespace.
    """
    return bool(HOUSEHOLD_SUFFIX.search((name or "").strip().casefold()))


def classify_brewery(brewery) -> str:
    """Assign a record category from the brewery type, then the name."""
    brewery_type = brewery.brewery_type

    if not brewery_type:
        if is_household(brewery.name):
            return "household"

        return "unclassified"

    # An explicit brewery type takes precedence over the name.
    return TYPE_CATEGORIES.get(brewery_type, "unclassified")
