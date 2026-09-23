import asyncio
from fastapi.testclient import TestClient

from app.main import fastapi_app
from app.services.chat_services import generate_chat_reply, get_cached_orchestrator, warm_start_cache


def test_chat_route_requires_auth():
    client = TestClient(fastapi_app)

    response = client.post("/chat/", json={"message": "Hello there"})

    assert response.status_code == 401


def test_generate_chat_reply_accepts_user_id():
    reply = asyncio.run(generate_chat_reply("Hello there", user_id="user-123"))
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_generate_chat_reply_rejects_empty_message():
    try:
        asyncio.run(generate_chat_reply("   "))
        assert False, "Expected ValueError for empty message"
    except ValueError:
        pass


def test_warm_start_cache_builds_cached_orchestrator():
    asyncio.run(warm_start_cache())

    orchestrator = asyncio.run(get_cached_orchestrator(
        "openai/gpt-oss-20b",
        "C:/Users/rajag_gc74h6t/OneDrive/Desktop/personal assistant",
        "default-user",
    ))

    assert orchestrator is not None
