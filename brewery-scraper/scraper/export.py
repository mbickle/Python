import json
from pathlib import Path
from typing import Any

from scraper.models import Brewery


def export_json(data, filename: str):
    """
    Export a JSON-serializable object to a file.
    """
    output_path = Path(filename)

    # Create the destination directory if necessary.
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def load_breweries(filename: str) -> tuple[list[Brewery], dict[str, Any]]:
    """
    Load a brewery export written by export_json().

    Returns the normalized records plus the run metadata that
    accompanied them (everything except the 'breweries' array).

    Raises:
        ValueError: If the file is not a brewery export payload.
        TypeError: If the 'breweries' value is not a list.
        pydantic.ValidationError: If a record does not match Brewery.
    """
    payload = json.loads(
        Path(filename).read_text(encoding="utf-8")
    )

    if not isinstance(payload, dict) or "breweries" not in payload:
        raise ValueError(f"{filename} is not a brewery export")

    records = payload["breweries"]

    if not isinstance(records, list):
        raise TypeError(f"{filename}: 'breweries' must be a list")

    breweries = [Brewery(**record) for record in records]

    metadata = {
        key: value
        for key, value in payload.items()
        if key != "breweries"
    }

    return breweries, metadata


def save_raw_records(records, filename: str) -> None:
    """
    Write source records to a cache file, compactly.

    Deliberately not pretty-printed: a source snapshot is around
    15 MB, and this file exists for reprocessing rather than reading.
    """
    output_path = Path(filename)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)


def load_raw_records(filename: str) -> list[dict[str, Any]]:
    """
    Load a raw source snapshot saved by save_raw_records().

    Raises:
        TypeError: If the file is not a JSON array of objects.
    """
    records = json.loads(
        Path(filename).read_text(encoding="utf-8")
    )

    if not isinstance(records, list):
        raise TypeError(f"{filename}: expected a JSON array of records")

    if not all(isinstance(item, dict) for item in records):
        raise TypeError(
            f"{filename}: expected every record to be a JSON object"
        )

    return records
