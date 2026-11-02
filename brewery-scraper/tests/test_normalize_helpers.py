import pytest

from scraper.normalize import (
    clean_text,
    get_country_code,
    normalize_breweries,
    normalize_brewery,
    normalize_code,
    normalize_flag,
    normalize_phone,
)


def test_clean_text_strips_whitespace():
    assert clean_text("  hello  ") == "hello"


def test_clean_text_empty_becomes_none():
    assert clean_text("") is None
    assert clean_text("   ") is None
    assert clean_text(None) is None


def test_clean_text_converts_to_string():
    assert clean_text(123) == "123"


def test_normalize_code_uppercases():
    assert normalize_code(" ca ") == "CA"
    assert normalize_code(None) is None
    assert normalize_code("  ") is None


def test_get_country_code_common_names():
    assert get_country_code("United States") == "US"
    assert get_country_code("germany") == "DE"


def test_get_country_code_overrides():
    assert get_country_code("Swaziland") == "SZ"
    assert get_country_code("Turkey") == "TR"


def test_get_country_code_unknown_returns_none():
    assert get_country_code("Narnia") is None
    assert get_country_code(None) is None
    assert get_country_code("  ") is None


def test_normalize_phone_valid_us_number():
    assert (
        normalize_phone("(206) 555-1234", "United States")
        == "+12065551234"
    )


def test_normalize_phone_invalid_returns_none():
    assert normalize_phone("not a phone", "United States") is None
    assert normalize_phone("", "United States") is None
    assert normalize_phone(None, "United States") is None


def test_normalize_brewery_single_record(raw_brewery):
    brewery = normalize_brewery(raw_brewery())

    assert brewery.id == "test-001"
    assert brewery.name == "Test Brewing"
    assert brewery.country_code == "US"
    assert brewery.record_category == "brewery"


def test_normalize_breweries_skips_invalid_record(capsys):
    raw_data = [
        {"Id": "001", "Name": "Good Brewing", "Brewery_Type__c": "Micro"},
        {"Name": "Missing Id Brewing"},  # no Id -> pydantic error
        {"Id": "003", "Name": "Also Good", "Brewery_Type__c": "Brewpub"},
    ]

    result = normalize_breweries(raw_data)

    assert len(result) == 2
    assert result[0].id == "001"
    assert result[1].id == "003"

    output = capsys.readouterr().out
    assert "skipping record" in output
    assert "Skipped 1 invalid" in output


def test_normalize_breweries_empty_list():
    assert normalize_breweries([]) == []


def test_normalize_breweries_skips_non_mapping_record():
    raw_data = [
        {"Id": "001", "Name": "Good Brewing", "Brewery_Type__c": "Micro"},
        "not a record",
    ]

    result = normalize_breweries(raw_data)

    assert len(result) == 1
    assert result[0].id == "001"


def test_normalize_breweries_does_not_swallow_code_bugs(monkeypatch):
    def boom(item):
        raise RuntimeError("bug in normalize_brewery")

    monkeypatch.setattr("scraper.normalize.normalize_brewery", boom)

    with pytest.raises(RuntimeError, match="bug in normalize_brewery"):
        normalize_breweries([{"Id": "001", "Name": "Test Brewing"}])


def test_normalize_flag_accepts_booleans():
    assert normalize_flag(True) is True
    assert normalize_flag(False) is False


@pytest.mark.parametrize("value", [None, "true", 1, "", "False"])
def test_normalize_flag_returns_none_for_other_values(value):
    assert normalize_flag(value) is None


def test_normalize_brewery_sets_craft_flag(raw_brewery):
    assert normalize_brewery(raw_brewery(craft=True)).is_craft_brewery is True
    assert normalize_brewery(raw_brewery(craft=False)).is_craft_brewery is False


def test_normalize_brewery_craft_flag_missing_is_none(raw_brewery):
    record = raw_brewery()
    record.pop("Is_Craft_Brewery__c")

    assert normalize_brewery(record).is_craft_brewery is None
