import argparse
from datetime import UTC, datetime

from rich import print

from scraper.diagnostics import (
    NORMALIZED_DIAGNOSTICS,
    RAW_DIAGNOSTICS,
    available_diagnostics,
    run_diagnostics,
)
from scraper.export import export_json, load_breweries
from scraper.fetch import fetch_url
from scraper.normalize import normalize_breweries
from scraper.stats import generate_stats

DEFAULT_SOURCE_URL = (
    "https://www.brewersassociation.org/"
    "wp-content/themes/ba2019/json-store/"
    "breweries/breweries.json"
)

DEFAULT_OUTPUT = "data/breweries.json"
DEFAULT_STATS_OUTPUT = "data/breweries-stats.json"
DEFAULT_DIAGNOSTICS_OUTPUT = "data/diagnostics.json"


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

    if args.input and args.url:
        parser.error("--input cannot be combined with --url")

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
        source_url = args.url or DEFAULT_SOURCE_URL

        source_metadata = {
            "source": "Brewers Association",
            "source_url": source_url,
            "schema_version": "1.0",
            "normalization_version": "1.0",
        }

        print("[cyan]Fetching Brewers Association records...[/cyan]")
        raw_data = fetch_url(source_url)
        record_count = len(raw_data)
        print(f"Fetched {record_count} records")

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

    print(f"[green]Exported {len(breweries)} records[/green]")
    print("[green]Done![/green]")

    return 0
