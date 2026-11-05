import argparse
from datetime import UTC, datetime
from pathlib import Path

from rich import print

from scraper.db_export import export_postgres, export_sqlite
from scraper.diagnostics import (
    NORMALIZED_DIAGNOSTICS,
    RAW_DIAGNOSTICS,
    available_diagnostics,
    run_diagnostics,
)
from scraper.export import (
    export_json,
    load_breweries,
    load_raw_records,
    save_raw_records,
)
from scraper.fetch import fetch_url
from scraper.normalize import normalize_breweries
from scraper.stats import generate_stats

DEFAULT_SOURCE_URL = (
    "https://www.brewersassociation.org/"
    "wp-content/themes/ba2019/json-store/"
    "breweries/breweries.json"
)

DEFAULT_OUTPUT = "data/breweries.json"
DEFAULT_SQLITE_OUTPUT = "data/breweries.db"
DEFAULT_STATS_OUTPUT = "data/breweries-stats.json"
DEFAULT_DIAGNOSTICS_OUTPUT = "data/diagnostics.json"

# Local cache for the downloaded source snapshot (gitignored).
DEFAULT_RAW_PATH = "data/raw/breweries.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Brewery Scraper")

    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help="Output JSON file",
    )

    parser.add_argument(
        "--url",
        type=str,
        help="Override source URL",
    )

    parser.add_argument(
        "--input",
        type=str,
        metavar="PATH",
        help="Reuse an existing brewery export instead of fetching",
    )

    parser.add_argument(
        "--raw-input",
        type=str,
        metavar="PATH",
        help="Use a saved raw source snapshot instead of downloading",
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Download the source again instead of using the cached copy",
    )

    parser.add_argument(
        "--sqlite-output",
        type=str,
        default=DEFAULT_SQLITE_OUTPUT,
        help="SQLite database output file",
    )

    parser.add_argument(
        "--skip-sqlite",
        action="store_true",
        help="Do not write the SQLite database",
    )

    parser.add_argument(
        "--postgres-url",
        type=str,
        metavar="DSN",
        help="PostgreSQL connection string; exports only when provided",
    )

    parser.add_argument(
        "--stats-output",
        type=str,
        default=DEFAULT_STATS_OUTPUT,
        help="Statistics JSON output file",
    )

    parser.add_argument(
        "--diagnostics",
        nargs="+",
        metavar="NAME",
        help="Run selected diagnostics (or 'all')",
    )

    parser.add_argument(
        "--list-diagnostics",
        action="store_true",
        help="List available diagnostic reports",
    )

    parser.add_argument(
        "--diagnostics-output",
        type=str,
        default=DEFAULT_DIAGNOSTICS_OUTPUT,
        help="Diagnostics JSON output file",
    )

    return parser


def _mode_conflicts(
    args: argparse.Namespace,
) -> list[tuple[str, list[str]]]:
    """Return (mode flag, conflicting flags) pairs for dataset modes."""
    conflicts = []

    if args.input:
        flags = [
            flag for flag, given in (
                ("--url", args.url),
                ("--raw-input", args.raw_input),
                ("--refresh", args.refresh),
            ) if given
        ]

        if flags:
            conflicts.append(("--input", flags))

    if args.raw_input:
        flags = [
            flag for flag, given in (
                ("--refresh", args.refresh),
                ("--url", args.url),
            ) if given
        ]

        if flags:
            conflicts.append(("--raw-input", flags))

    return conflicts


def _validate_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    """Reject unusable argument combinations before any I/O happens."""
    if args.diagnostics:
        available = set(available_diagnostics())

        unknown = [
            name for name in args.diagnostics
            if name != "all" and name not in available
        ]

        if unknown:
            parser.error("Unknown diagnostics: " + ", ".join(unknown))

    for mode, flags in _mode_conflicts(args):
        parser.error(
            f"{mode} cannot be combined with " + " or ".join(flags)
        )

    if args.input and not Path(args.input).is_file():
        parser.error(
            f"--input file not found: {args.input}. "
            "Run without --input to download and create it, "
            "or point --input at an existing brewery export."
        )

    if args.input and args.diagnostics:
        # A saved export holds normalized records only, so reports that
        # need raw source dictionaries cannot run from it.
        unavailable = [
            name for name in args.diagnostics
            if name == "all" or name in RAW_DIAGNOSTICS
        ]

        if unavailable:
            normalized = ", ".join(sorted(NORMALIZED_DIAGNOSTICS))

            parser.error(
                "--input provides normalized records only; raw diagnostics "
                "need a live fetch: " + ", ".join(unavailable) +
                ". Run normalized reports individually: " + normalized
            )


def _file_timestamp(path: Path) -> str | None:
    """Return a file's modification time as an ISO timestamp."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    except OSError:
        return None


def _acquire_raw_data(args: argparse.Namespace) -> tuple[list, dict]:
    """Load raw source records from disk, or download and cache them."""
    if args.raw_input:
        path = Path(args.raw_input)
        print(f"[cyan]Loading raw source from {path}...[/cyan]")

        return load_raw_records(str(path)), {
            "raw_source": str(path),
            "raw_fetched_at": _file_timestamp(path),
        }

    cache_path = Path(DEFAULT_RAW_PATH)

    if cache_path.exists() and not args.refresh and not args.url:
        fetched_at = _file_timestamp(cache_path)

        print(
            f"[yellow]Using cached source:[/yellow] {cache_path} "
            f"(downloaded {fetched_at})"
        )
        print("[yellow]Pass --refresh to download it again.[/yellow]")

        return load_raw_records(str(cache_path)), {
            "raw_source": str(cache_path),
            "raw_fetched_at": fetched_at,
        }

    source_url = args.url or DEFAULT_SOURCE_URL
    raw_data = fetch_url(source_url)

    metadata = {"raw_fetched_at": datetime.now(UTC).isoformat()}

    if raw_data:
        save_raw_records(raw_data, str(cache_path))
        print(f"[cyan]Cached raw source at {cache_path}[/cyan]")
        metadata["raw_source"] = str(cache_path)
    else:
        # Never let an empty response replace a usable cache.
        print(
            "[yellow]Source returned no records; "
            "cache left untouched[/yellow]"
        )

    return raw_data, metadata


def _build_metadata(
    args: argparse.Namespace,
    breweries: list,
    record_count: int,
    source_metadata: dict,
) -> dict:
    """Combine run metadata with whatever the input file already carried."""
    metadata = {
        **source_metadata,
        "generated_at": datetime.now(UTC).isoformat(),
        "count": record_count,
        "normalized_count": len(breweries),
    }

    if args.input:
        metadata["input"] = args.input

    return metadata


def main(argv: list[str] | None = None) -> int:
    """Run the command-line pipeline. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_diagnostics:
        print("\nAvailable diagnostics:")

        for name in available_diagnostics():
            print(f"  {name}")

        return 0

    _validate_args(parser, args)

    raw_data = None

    if args.input:
        print(f"[cyan]Loading records from {args.input}...[/cyan]")
        breweries, source_metadata = load_breweries(args.input)
        record_count = len(breweries)
        print(f"Loaded {record_count} records")
    else:
        raw_data, raw_metadata = _acquire_raw_data(args)
        record_count = len(raw_data)

        source_metadata = {
            "source": None if args.raw_input else "Brewers Association",
            "source_url": (
                None
                if args.raw_input
                else (args.url or DEFAULT_SOURCE_URL)
            ),
            **raw_metadata,
            "schema_version": "1.0",
            "normalization_version": "1.0",
        }

        print(f"Loaded {record_count} raw records")

        print("[cyan]Normalizing and classifying...[/cyan]")
        breweries = normalize_breweries(raw_data)

    # Run diagnostics only when requested.
    diagnostic_results = None

    if args.diagnostics:
        print("[yellow]Running diagnostics...[/yellow]")

        diagnostic_results = run_diagnostics(
            args.diagnostics,
            raw_data,
            breweries,
        )

    metadata = _build_metadata(args, breweries, record_count, source_metadata)

    if args.input:
        # Nothing new to write: the records came from the output path.
        print("[yellow]Skipping brewery export (--input)[/yellow]")
    else:
        brewery_payload = {
            **metadata,
            "breweries": [
                brewery.model_dump()
                for brewery in breweries
            ],
        }

        print(f"[cyan]Exporting to {args.output}...[/cyan]")
        export_json(brewery_payload, args.output)

    stats_payload = {
        **metadata,
        "stats": generate_stats(breweries),
    }

    print(f"[cyan]Exporting stats to {args.stats_output}...[/cyan]")
    export_json(stats_payload, args.stats_output)

    # Export diagnostics only when requested.
    if diagnostic_results is not None:
        diagnostic_payload = {
            **metadata,
            "diagnostics": diagnostic_results,
        }

        print(
            f"[cyan]Exporting diagnostics to "
            f"{args.diagnostics_output}...[/cyan]"
        )

        export_json(diagnostic_payload, args.diagnostics_output)

    if not args.skip_sqlite:
        print(
            f"[cyan]Exporting SQLite database to "
            f"{args.sqlite_output}...[/cyan]"
        )
        export_sqlite(breweries, metadata, args.sqlite_output)

    if args.postgres_url:
        print("[cyan]Exporting to PostgreSQL...[/cyan]")
        export_postgres(breweries, metadata, args.postgres_url)

    print(f"[green]Exported {len(breweries)} records[/green]")
    print("[green]Done![/green]")

    return 0
