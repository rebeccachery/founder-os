"""API smoke tests against a throwaway SQLite database."""

import pytest
from fastapi.testclient import TestClient

HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture
def client(isolated_env):
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def opportunity_id(client):
    response = client.post(
        "/api/opportunities/saved",
        json={
            "url": "https://grants.example.org/ai-literacy",
            "name": "AI Literacy Grant",
            "description": "Pre-seed AI education grant for language learning. Deadline: 2030-01-15",
        },
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_health_is_public(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
def test_api_routes_require_key(client, headers):
    assert client.get("/api/stats", headers=headers).status_code == 401


def test_saved_opportunity_is_scored_listed_and_auto_tracked(client, opportunity_id):
    listing = client.get("/api/scout", headers=HEADERS).json()
    items = listing if isinstance(listing, list) else listing.get("items", listing)
    match = next(item for item in items if item["id"] == opportunity_id)
    assert match["score_total"] > 0
    assert match["source"] == "manual"

    tracks = client.get("/api/assistant/tracks", headers=HEADERS).json()
    assert any(t["source_id"] == opportunity_id and t["track_application"] for t in tracks)


def test_pin_then_untrack(client, opportunity_id):
    pinned = client.put(
        f"/api/assistant/tracks/{opportunity_id}", json={"pin_priority": True}, headers=HEADERS
    )
    assert pinned.status_code == 200
    assert pinned.json()["pin_priority"] is True

    briefing = client.get("/api/briefing", headers=HEADERS).json()
    assert briefing["priorities"][0]["source_id"] == opportunity_id  # pinned goes first

    assert client.delete(f"/api/assistant/tracks/{opportunity_id}", headers=HEADERS).status_code == 200


def test_application_draft_round_trip(client, opportunity_id):
    path = f"/api/applications/scout_opportunities/{opportunity_id}/draft"
    saved = client.put(path, json={"body": "Our mission is..."}, headers=HEADERS)
    assert saved.status_code == 200
    assert client.get(path, headers=HEADERS).json()["body"] == "Our mission is..."


def test_deadline_edit_validates_input(client, opportunity_id):
    ok = client.patch(f"/api/scout/{opportunity_id}", json={"deadline_at": "2031-02-01"}, headers=HEADERS)
    assert ok.status_code == 200
    missing = client.patch("/api/scout/999999", json={"deadline_at": "2031-02-01"}, headers=HEADERS)
    assert missing.status_code == 404


def test_lists_agents_with_schedules(client):
    body = client.get("/api/agents", headers=HEADERS).json()
    assert body["schedules"]["funding_scout"] == "daily"
    assert set(body["agents"]) >= {"funding_scout", "executive_assistant", "oss_discovery"}
