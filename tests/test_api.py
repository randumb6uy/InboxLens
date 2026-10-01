"""Tests for FastAPI backend REST API routes."""

from fastapi.testclient import TestClient
import pytest

from src.api.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_api_overview():
    res = client.get("/api/stats/overview")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "classification" in data


def test_api_spend():
    res = client.get("/api/stats/spend")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert "transactions" in data


def test_api_subscriptions():
    res = client.get("/api/subscriptions")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_api_newsletters():
    res = client.get("/api/newsletters")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_api_important_contacts():
    res = client.get("/api/contacts/important")
    assert res.status_code == 200
    data = res.json()
    assert "vip_contacts" in data
    assert "recent_threads" in data


def test_api_add_important_contact():
    # Valid email
    res = client.post(
        "/api/contacts/important",
        json={"email": "mentor@advisors.com", "display_name": "Mentor", "notes": "VIP"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Invalid email
    bad_res = client.post(
        "/api/contacts/important",
        json={"email": "invalid-email-string"},
    )
    assert bad_res.status_code == 400


def test_api_schedule():
    res = client.get("/api/schedule/upcoming")
    assert res.status_code == 200
    data = res.json()
    assert "meetings" in data
    assert "deadlines" in data


def test_api_jobs():
    res = client.get("/api/jobs")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_api_sync_inbox():
    res = client.post("/api/inbox/sync", json={"limit": 20, "mock": True})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["ingested_count"] == 20
