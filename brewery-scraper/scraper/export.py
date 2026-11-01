import json
from pathlib import Path


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
