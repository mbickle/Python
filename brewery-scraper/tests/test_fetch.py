import pytest
import requests

from scraper.fetch import fetch_url


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_fetch_url_success(monkeypatch):
    payload = [{"Id": "001"}, {"Id": "002"}]
    monkeypatch.setattr(
        "requests.get", lambda url, timeout: FakeResponse(payload)
    )

    assert fetch_url("https://example.com/x.json") == payload


def test_fetch_url_rejects_non_list(monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout: FakeResponse({"not": "a list"}),
    )

    with pytest.raises(TypeError):
        fetch_url("https://example.com/x.json", retries=1)


def test_fetch_url_rejects_non_dict_items(monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout: FakeResponse([{"Id": "1"}, "nope"]),
    )

    with pytest.raises(TypeError):
        fetch_url("https://example.com/x.json", retries=1)


def test_fetch_url_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky_get(url, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("boom")
        return FakeResponse([{"Id": "001"}])

    monkeypatch.setattr("requests.get", flaky_get)
    monkeypatch.setattr("scraper.fetch.time.sleep", lambda s: None)

    result = fetch_url("https://example.com/x.json", retries=3, delay=0)

    assert result == [{"Id": "001"}]
    assert calls["n"] == 3


def test_fetch_url_raises_after_retries_exhausted(monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout: (_ for _ in ()).throw(
            requests.ConnectionError("down")
        ),
    )
    monkeypatch.setattr("scraper.fetch.time.sleep", lambda s: None)

    with pytest.raises(requests.RequestException):
        fetch_url("https://example.com/x.json", retries=2, delay=0)


def test_fetch_url_rejects_bad_retry_count():
    with pytest.raises(ValueError):
        fetch_url("https://example.com/x.json", retries=0)
