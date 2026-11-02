import phonenumbers
import pycountry
from pydantic import ValidationError
from rich import print

from scraper.classify import classify_brewery
from scraper.models import Brewery

# Country names that pycountry may not recognize directly.
# Keys are normalized source names; values are ISO alpha-2 codes.
COUNTRY_OVERRIDES = {
    "swaziland": "SZ",
    "turkey": "TR",
    "reunion": "RE",
    "aland islands": "AX",
    "cote d'ivoire": "CI",
    "ivory coast": "CI",
}

def clean_text(value):
    """
    Clean up text fields without changing their meaning.
    Returns None for empty or whitespace-only values.
    """
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def normalize_code(value):
    """
    Standardize geographic codes.
    Example: ' ca ' becomes 'CA'.
    """
    value = clean_text(value)

    if not value:
        return None

    return value.upper()

def get_country_code(country_name):
    """
    Convert a country name into an ISO alpha-2 country code.
    """
    country_name = clean_text(country_name)

    if not country_name:
        return None

    # Check known exceptions first.
    override = COUNTRY_OVERRIDES.get(country_name.casefold())

    if override:
        return override

    try:
        country = pycountry.countries.lookup(country_name)
        return country.alpha_2

    except LookupError:
        return None

def normalize_phone(phone, country):
    """
    Convert phone numbers into international E.164 format.
    """
    phone = clean_text(phone)

    if not phone:
        return None

    region = get_country_code(country)

    try:
        parsed = phonenumbers.parse(phone, region)

        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )

    except phonenumbers.NumberParseException:
        pass

    return None

def normalize_breweries(raw_data):
    breweries = []
    skipped = 0

    for index, item in enumerate(raw_data):
        try:
            breweries.append(normalize_brewery(item))
        # Deliberately narrow to malformed-record errors: one bad
        # record must not abort the run, but real bugs still should.
        except (AttributeError, TypeError, ValidationError) as ex:
            skipped += 1
            print(
                f"[yellow]Warning: skipping record "
                f"at index {index}: {ex}[/yellow]"
            )

    if skipped:
        print(
            f"[yellow]Skipped {skipped} invalid "
            f"record(s) out of {len(raw_data)}[/yellow]"
        )

    return breweries


def normalize_brewery(item):
    address = item.get("BillingAddress") or {}
    country = clean_text(address.get("country"))
    parent = item.get("Parent") or {}

    brewery = Brewery(
        id=item.get("Id"),
        name=clean_text(item.get("Name")) or "Unknown",

        brewery_type=clean_text(
            item.get("Brewery_Type__c")
        ),

        phone=clean_text(item.get("Phone")),
        phone_normalized=normalize_phone(
            item.get("Phone"),
            country
        ),
        website=clean_text(item.get("Website")),

        street=clean_text(address.get("street")),
        city=clean_text(address.get("city")),

        state=clean_text(address.get("state")),
        state_code=normalize_code(
            address.get("stateCode")
        ),

        postal_code=clean_text(
            address.get("postalCode")
        ),

        country=country,
        country_code=get_country_code(country),

        latitude=address.get("latitude"),
        longitude=address.get("longitude"),

        parent_id=parent.get("Id"),
        parent_name=parent.get("Name"),
    )

    brewery.record_category = classify_brewery(brewery)
    return brewery
