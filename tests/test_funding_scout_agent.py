"""End-to-end: search results in → filtered, ranked, deduped rows + digest out."""

import json
from pathlib import Path

import pytest

import agents.funding_scout.agent as scout_module
from agents.funding_scout.agent import FundingScoutAgent
from lib.schemas import SearchResult

AGENT_DIR = Path(scout_module.__file__).parent


@pytest.fixture
def agent(conn, isolated_env, monkeypatch):
    monkeypatch.setattr(scout_module, "REPORTS_DIR", isolated_env / "reports")
    return FundingScoutAgent(conn, AGENT_DIR)


def _hit(url, title="AI EdTech grant", snippet="Pre-seed AI education grant. Deadline: Dec 1, 2030", **kw):
    return SearchResult(title=title, url=url, snippet=snippet, source="tavily", category="grants", **kw)


def test_filters_low_quality_results_and_stores_the_rest(agent, conn):
    results = [
        _hit("https://grants.example.org/ai-edtech?utm_source=newsletter"),
        _hit("https://twitter.com/someone/status/1"),  # social post, not an application page
        _hit("not a url"),
        _hit("https://en.wikipedia.org/wiki/Language", source_relevance=0.05),  # off-topic
    ]
    outcome = agent.process_results(results)

    assert outcome.items_found == 4
    assert outcome.items_upserted == 1
    assert "3 low-quality results skipped" in outcome.message

    row = conn.execute("SELECT * FROM scout_opportunities").fetchone()
    assert row["url"] == "https://grants.example.org/ai-edtech"  # tracking params stripped
    assert row["deadline_at"] == "2030-12-01"
    assert row["score_total"] > 0
    assert row["category"] == "grants"


def test_rescan_without_date_keeps_previously_found_deadline(agent, conn):
    agent.process_results([_hit("https://grants.example.org/a")])
    agent.process_results([_hit("https://grants.example.org/a", snippet="AI education grant")])
    rows = conn.execute("SELECT deadline_at FROM scout_opportunities").fetchall()
    assert len(rows) == 1
    assert rows[0]["deadline_at"] == "2030-12-01"


def test_flags_likely_duplicates_across_urls(agent, conn):
    agent.process_results([_hit("https://a.example.org/program", title="Global AI Founders Fellowship 2026")])
    agent.process_results([_hit("https://b.example.org/program", title="Global AI Founders Fellowship 2026")])
    raw = conn.execute(
        "SELECT raw_json FROM scout_opportunities WHERE url = 'https://b.example.org/program'"
    ).fetchone()["raw_json"]
    assert "likely_duplicate_of" in json.loads(raw)


def test_writes_ranked_digest(agent, isolated_env):
    agent.process_results(
        [
            _hit("https://low.example.org", title="Bakery expo", snippet="cakes"),
            _hit("https://high.example.org"),
        ]
    )
    digest = next((isolated_env / "reports").glob("scout_*.md")).read_text()
    assert digest.index("AI EdTech grant") < digest.index("Bakery expo")


def test_zero_results_is_reported_as_error(agent):
    outcome = agent.process_results([])
    assert outcome.status == "error"
    assert "search provider" in outcome.message
