import sys
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Ensure microservice root is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from main import app, ces_session_service

client = TestClient(app)


def _mock_sessions(structured_response):
    mock = MagicMock()
    mock.run.return_value = MagicMock()
    mock.get_structured_response.return_value = structured_response
    return mock


def test_send_chat_message_returns_agent_text_and_widget(monkeypatch):
    monkeypatch.setattr(
        ces_session_service,
        "sessions",
        _mock_sessions({
            "agent_text": "Here are a few running shoes for you.",
            "payload": {"productDetails": [{"title": "Trail Runner", "price": "$89.99"}]},
            "session_ended": False,
            "agent_transfer": "ShoppingAssistant",
        }),
    )

    response = client.post(
        "/api/v1/chat/test-session-1/messages",
        json={"text": "show me some running shoes", "user_id": "u_1029"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["text"] == "Here are a few running shoes for you."
    assert data["widget"]["productDetails"][0]["title"] == "Trail Runner"
    assert data["session_ended"] is False
    assert data["agent_transfer"] == "ShoppingAssistant"

    called_kwargs = ces_session_service.sessions.run.call_args.kwargs
    assert called_kwargs["session_id"] == "test-session-1"
    assert called_kwargs["text"] == "show me some running shoes"
    assert called_kwargs["variables"] == {"user_id": "u_1029"}


def test_send_chat_message_guest_omits_user_id_variable(monkeypatch):
    monkeypatch.setattr(
        ces_session_service,
        "sessions",
        _mock_sessions({
            "agent_text": "Welcome! How can I help you shop today?",
            "payload": None,
            "session_ended": False,
            "agent_transfer": None,
        }),
    )

    response = client.post(
        "/api/v1/chat/test-session-2/messages",
        json={"text": "hello"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["widget"] is None

    called_kwargs = ces_session_service.sessions.run.call_args.kwargs
    assert called_kwargs["variables"] is None


def test_send_chat_message_failure_returns_400(monkeypatch):
    monkeypatch.setattr(ces_session_service, "sessions", None)

    response = client.post(
        "/api/v1/chat/test-session-3/messages",
        json={"text": "hello"},
    )

    assert response.status_code == 400
