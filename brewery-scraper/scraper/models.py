from pydantic import BaseModel


class Brewery(BaseModel):
    id: str
    name: str

    brewery_type: str | None = None

    street: str | None = None
    city: str | None = None
    state: str | None = None
    state_code: str | None = None

    postal_code: str | None = None
    country: str | None = None
    country_code: str | None = None

    website: str | None = None
    phone: str | None = None
    phone_normalized: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    parent_id: str | None = None
    parent_name: str | None = None
    record_category: str | None = None

    # Source's craft designation flag (Is_Craft_Brewery__c); not derived.
    is_craft_brewery: bool | None = None
