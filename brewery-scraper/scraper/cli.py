import argparse
from datetime import UTC, datetime

from rich import print

from scraper.diagnostics import available_diagnostics, run_diagnostics
from scraper.export import export_json
from scraper.fetch import fetch_url
from scraper.normalize import normalize_breweries
from scraper.stats import generate_stats


def run_cli():
    parser = argparse.ArgumentParser(
        description="Brewery Scraper"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/breweries.json",
        help="Output JSON file"
    )

    parser.add_argument(
        "--url",
        type=str,
        help="Override source URL"
    )

    parser.add_argument(
        "--stats-output",
        type=str,
        default="data/breweries-stats.json",
        help="Statistics JSON output file"
    )

    parser.add_argument(
        "--diagnostics",
        nargs="+",
        metavar="NAME",
        help="Run selected diagnostics (or 'all')"
    )

    parser.add_argument(
        "--list-diagnostics",
        action="store_true",
        help="List available diagnostic reports"
    )

    parser.add_argument(
        "--diagnostics-output",
        type=str,
        default="data/diagnostics.json",
        help="Diagnostics JSON output file"
    )    

    args = parser.parse_args()

    if args.list_diagnostics:
        print("\nAvailable diagnostics:")

        for name in available_diagnostics():
            print(f"  {name}")

        return

    # Validate diagnostic names before fetching any data.
    if args.diagnostics:
        available = set(available_diagnostics())

        unknown = [
            name for name in args.diagnostics
            if name != "all" and name not in available
        ]

        if unknown:
            parser.error(
                "Unknown diagnostics: " + ", ".join(unknown)
            )

    source_url = args.url or (
        "https://www.brewersassociation.org/"
        "wp-content/themes/ba2019/json-store/"
        "breweries/breweries.json"
    )

    print("[cyan]Fetching Brewers Association records...[/cyan]")
    raw_data = fetch_url(source_url)

    print(f"Fetched {len(raw_data)} records")

    print("[cyan]Normalizing and classifying...[/cyan]")
    breweries = normalize_breweries(raw_data)

    # Run diagnostics only when requested.
    diagnostic_results = None

    if args.diagnostics:
        print("[yellow]Running diagnostics...[/yellow]")

        diagnostic_results = run_diagnostics(
            args.diagnostics,
            raw_data,
            breweries
        )

    metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "Brewers Association",
        "source_url": source_url,
        "schema_version": "1.0",
        "normalization_version": "1.0",
        "count": len(raw_data),
        "normalized_count": len(breweries),
    }

    # Create the brewery export payload.
    brewery_payload = {
        **metadata,
        "breweries": [
            brewery.model_dump()
            for brewery in breweries
        ]
    }

    # Create the statistics export payload.
    stats_payload = {
        **metadata,
        "stats": generate_stats(breweries)
    }

    # Export files.
    print(f"[cyan]Exporting to {args.output}...[/cyan]")
    export_json(brewery_payload, args.output)

    print(f"[cyan]Exporting stats to {args.stats_output}...[/cyan]")
    export_json(stats_payload, args.stats_output)

    # Export diagnostics only when requested.
    if diagnostic_results is not None:
        diagnostic_payload = {
            **metadata,
            "diagnostics": diagnostic_results
        }

        print(
            f"[cyan]Exporting diagnostics to "
            f"{args.diagnostics_output}...[/cyan]"
        )

        export_json(
            diagnostic_payload,
            args.diagnostics_output
        )    

    print(f"[green]Exported {len(breweries)} records[/green]")
    print("[green]Done![/green]")
