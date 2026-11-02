import pytest

import main as cli_entry


def test_run_returns_the_cli_status(monkeypatch):
    monkeypatch.setattr(cli_entry, "main", lambda argv=None: 7)

    assert cli_entry.run([]) == 7


def test_run_treats_a_closed_pipe_as_a_clean_stop(monkeypatch):
    def explode(argv=None):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr(cli_entry, "main", explode)
    monkeypatch.setattr(cli_entry, "_stdout_is_broken", lambda: True)

    redirected = {}
    monkeypatch.setattr(
        cli_entry,
        "_redirect_stdout_to_devnull",
        lambda: redirected.setdefault("done", True),
    )

    assert cli_entry.run([]) == 0
    assert redirected["done"] is True


def test_run_reraises_errors_unrelated_to_the_pipe(monkeypatch):
    def explode(argv=None):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(cli_entry, "main", explode)
    monkeypatch.setattr(cli_entry, "_stdout_is_broken", lambda: False)

    with pytest.raises(OSError):
        cli_entry.run([])
