import json

from scraper.export import export_json


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
    assert "\\u" not in content
