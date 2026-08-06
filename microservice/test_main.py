import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure microservice root is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

import main
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "shopping-user-service"

def test_get_user_profile_u1029():
    response = client.get("/api/v1/users/u_1029")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["user_id"] == "u_1029"
    assert data["user_name"] == "Alex"
    assert data["membership_tier"] == "gold"
    assert isinstance(data["memories"], list)

def test_add_user_memory():
    payload = {"fact": "User prefers trail running shoes."}
    response = client.post("/api/v1/users/u_1029/memories", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["user_id"] == "u_1029"

def test_update_user_preferences_merges_and_dedupes():
    response = client.post("/api/v1/users/u_1029/preferences", json={
        "preferred_categories": ["shoes"],
        "preferred_sports": ["running"],
        "shoe_size": "10",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["preferences"]["preferred_categories"] == ["shoes"]
    assert data["preferences"]["shoe_size"] == "10"

    # A second, overlapping update should union list fields and overwrite scalars
    response2 = client.post("/api/v1/users/u_1029/preferences", json={
        "preferred_categories": ["shoes", "apparel"],
        "shoe_size": "11",
        "price_max": 150.0,
    })
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["preferences"]["preferred_categories"] == ["shoes", "apparel"]
    assert data2["preferences"]["shoe_size"] == "11"
    assert data2["preferences"]["price_max"] == 150.0
    # preferred_sports from the first call should still be present (merge, not overwrite)
    assert data2["preferences"]["preferred_sports"] == ["running"]

def test_get_user_profile_includes_preferences():
    response = client.get("/api/v1/users/u_1029")
    assert response.status_code == 200
    data = response.json()
    assert "preferences" in data


def test_health_check_bypasses_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-secret-key")
    response = client.get("/health")
    assert response.status_code == 200


def test_rejects_request_missing_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-secret-key")
    response = client.get("/api/v1/users/u_1029")
    assert response.status_code == 401


def test_rejects_request_with_wrong_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-secret-key")
    response = client.get("/api/v1/users/u_1029", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_accepts_request_with_correct_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-secret-key")
    response = client.get("/api/v1/users/u_1029", headers={"X-API-Key": "test-secret-key"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_post_routes_also_require_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-secret-key")
    response = client.post("/api/v1/users/u_1029/memories", json={"fact": "test"})
    assert response.status_code == 401
    response = client.post("/api/v1/users/u_1029/preferences", json={"shoe_size": "10"})
    assert response.status_code == 401


def test_record_feedback_persists_rating_and_comments():
    response = client.post("/api/v1/users/u_1029/feedback", json={
        "feedback_id": "fb_test_001",
        "rating": 5,
        "comments": "Loved the recommendations!",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["feedback_id"] == "fb_test_001"


def test_record_feedback_clamps_rating_range():
    response = client.post("/api/v1/users/u_1029/feedback", json={
        "feedback_id": "fb_test_002",
        "rating": 7,
        "comments": "too high",
    })
    assert response.status_code == 422  # Pydantic rejects out-of-range rating


def test_record_feedback_requires_api_key(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-secret-key")
    response = client.post("/api/v1/users/u_1029/feedback", json={
        "feedback_id": "fb_test_003",
        "rating": 4,
        "comments": "",
    })
    assert response.status_code == 401
