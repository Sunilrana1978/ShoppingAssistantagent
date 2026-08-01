import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure microservice root is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

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

def test_before_agent_webhook():
    payload = {
        "state": {
            "user_id": "u_1029"
        }
    }
    response = client.post("/api/v1/webhooks/before-agent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["updatedVariables"]["user_name"] == "Alex"
    assert data["updatedVariables"]["membership_tier"] == "gold"

def test_after_tool_webhook():
    payload = {
        "tool_name": "add_to_cart",
        "state": {
            "user_id": "u_1029"
        },
        "tool_response": {
            "cart": {
                "items": [{"sku": "sku_1029", "name": "TrailBlaze Pro", "size": "10", "qty": 1}],
                "total": 110.49
            }
        }
    }
    response = client.post("/api/v1/webhooks/after-tool", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
