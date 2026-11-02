import json

import pytest

from scraper.export import export_json, load_breweries


def test_export_json_writes_file(tmp_path):
    target = tmp_path / "out.json"
    data = {"hello": "world", "n": 42}

    export_json(data, str(target))

    assert json.loads(target.read_text(encoding="utf-8")) == data


def test_export_json_creates_parent_dirs(tmp_path):
    target = tmp_path / "nested" / "dir" / "out.json"

    export_json({"a": 1}, str(target))

    assert target.exists()


def test_export_json_preserves_unicode(tmp_path):
    target = tmp_path / "out.json"

    export_json({"name": "Brasserie Dupont"}, str(target))

    content = target.read_text(encoding="utf-8")
    assert "Brasserie Dupont" in content
    # ensure_ascii=False means no \uXXXX escapes
    assert chr(92) + "u" not in content


def test_load_breweries_round_trip(tmp_path):
    target = tmp_path / "breweries.json"

    export_json({
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source": "Brewers Association",
        "count": 1,
        "normalized_count": 1,
        "breweries": [
            {
                "id": "001",
                "name": "Alpha Brewing",
                "record_category": "brewery",
                "country_code": "US",
            }
        ],
    }, str(target))

    breweries, metadata = load_breweries(str(target))

    assert len(breweries) == 1
    assert breweries[0].name == "Alpha Brewing"
    assert breweries[0].country_code == "US"
    assert metadata["source"] == "Brewers Association"
    assert "breweries" not in metadata


def test_load_breweries_rejects_other_json(tmp_path):
    target = tmp_path / "other.json"
    export_json({"hello": "world"}, str(target))

    with pytest.raises(ValueError, match="not a brewery export"):
        load_breweries(str(target))
