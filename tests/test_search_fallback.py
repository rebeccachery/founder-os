import httpx
import pytest

from lib.schemas import SearchResult
from lib.search import client


def _result(url: str, source: str) -> SearchResult:
    return SearchResult(title="t", url=url, source=source)


@pytest.fixture
def fake_providers(monkeypatch):
    calls: list[str] = []

    def failing(query, **_):
        calls.append("tavily")
        raise httpx.HTTPStatusError(
            "429", request=httpx.Request("POST", "https://x"), response=httpx.Response(429)
        )

    def empty(query, **_):
        calls.append("serpapi")
        return []

    def working(query, **_):
        calls.append("google_cse")
        return [_result("https://ok.example", "google_cse")]

    monkeypatch.setattr(client, "PROVIDERS", {"tavily": failing, "serpapi": empty, "google_cse": working})
    monkeypatch.setenv("SEARCH_FALLBACK_ORDER", "tavily,serpapi,google_cse")
    return calls


def test_falls_back_past_errors_and_empty_results(fake_providers):
    results = client.search("ai grants")
    assert [r.source for r in results] == ["google_cse"]
    assert fake_providers == ["tavily", "serpapi", "google_cse"]


def test_stops_at_first_provider_with_results(fake_providers, monkeypatch):
    monkeypatch.setenv("SEARCH_FALLBACK_ORDER", "google_cse,tavily")
    client.search("ai grants")
    assert fake_providers == ["google_cse"]


def test_explicit_provider_does_not_fall_back(fake_providers):
    with pytest.raises(httpx.HTTPStatusError):
        client.search("ai grants", provider="tavily")


def test_unknown_providers_are_skipped(fake_providers, monkeypatch):
    monkeypatch.setenv("SEARCH_FALLBACK_ORDER", "bing, google_cse")
    assert len(client.search("q")) == 1


def test_no_keys_means_no_results_not_an_error(monkeypatch):
    # Real providers return [] when their API key is missing (conftest unsets them).
    monkeypatch.setenv("SEARCH_FALLBACK_ORDER", "tavily,serpapi,google_cse")
    assert client.search("anything") == []
