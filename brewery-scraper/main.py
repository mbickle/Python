import os
import sys

from scraper.cli import main


def _stdout_is_broken() -> bool:
    """Return True when the reader has closed stdout's pipe."""
    try:
        sys.stdout.flush()
    except (BrokenPipeError, OSError):
        return True

    return False


def _redirect_stdout_to_devnull() -> None:
    """Aim stdout at the null device so shutdown flush cannot fail."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (OSError, ValueError):
        pass


def run(argv: list[str] | None = None) -> int:
    """Run the CLI, treating a closed output pipe as a clean stop."""
    try:
        status = main(argv)
        sys.stdout.flush()

        return status
    except (BrokenPipeError, OSError):
        # Windows reports a closed pipe as OSError(22) rather than EPIPE,
        # so only swallow it when stdout really is unwritable.
        if not _stdout_is_broken():
            raise

        _redirect_stdout_to_devnull()

        return 0


if __name__ == "__main__":
    sys.exit(run())
