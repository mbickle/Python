
import time
from typing import Any

import requests
from rich import print


def fetch_url(
    url: str,
    retries: int = 3,
    delay: float = 1.0
) -> list[dict[str, Any]]:
    """
    Fetch raw brewery records from a JSON endpoint.

    Retries failed requests up to the specified number of times.

    Args:
        url: URL of the JSON endpoint.
        retries: Maximum number of attempts.
        delay: Seconds to wait between attempts.

    Returns:
        List of raw Salesforce record dictionaries.

    Raises:
        requests.RequestException: If an HTTP request fails
            after all retries.
        ValueError: If the response contains unexpected data.
    """
    if retries < 1:
        raise ValueError("retries must be at least 1")

    for attempt in range(1, retries + 1):
        try:
            print(f"[yellow]Fetching:[/yellow] {url}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Validate the structure before returning.
            if not isinstance(data, list):
                raise TypeError(
                    "Expected a JSON array of brewery records"
                )

            if not all(isinstance(item, dict) for item in data):
                raise TypeError(
                    "Expected every brewery record to be a JSON object"
                )

            return data

        except (requests.RequestException, ValueError) as ex:
            print(f"[red]Attempt {attempt} failed:[/red] {ex}")

            if attempt < retries:
                time.sleep(delay)
            else:
                raise

    # This should never be reached because the final failed
    # attempt raises an exception.
    raise RuntimeError("Fetch failed unexpectedly")
