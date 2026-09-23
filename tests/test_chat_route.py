from fastapi.testclient import TestClient

from app.main import fastapi_app
from app.services.chat_services import generate_chat_reply


def test_chat_route_requires_auth():
    client = TestClient(fastapi_app)

    response = client.post("/chat/", json={"message": "Hello there"})

    assert response.status_code == 401


def test_generate_chat_reply_accepts_user_id():
    reply = generate_chat_reply("Hello there", user_id="user-123")
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_generate_chat_reply_rejects_empty_message():
    try:
        generate_chat_reply("   ")
        assert False, "Expected ValueError for empty message"
    except ValueError:
        pass
