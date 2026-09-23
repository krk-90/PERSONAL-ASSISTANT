import os
import asyncio
from pathlib import Path
from typing import Any

from agent.graph.orchestrator.orchestrator import create_orchestrator, get_orchestrator_response
from llm_gateway.provider.groq_llm import get_model

_ORCHESTRATOR_CACHE: dict[tuple[str, str, str], Any] = {}
_ORCHESTRATOR_CACHE_LOCK = asyncio.Lock()


def invalidate_orchestrator_cache(user_id: str) -> None:
    for key in list(_ORCHESTRATOR_CACHE):
        if key[2] == user_id:
            del _ORCHESTRATOR_CACHE[key]


async def get_cached_orchestrator(model_name: str, repo_path: str, user_id: str):
    key = (model_name, repo_path, user_id)
    if key not in _ORCHESTRATOR_CACHE:
        async with _ORCHESTRATOR_CACHE_LOCK:
            if key not in _ORCHESTRATOR_CACHE:
                llm = get_model(model_name)
                _ORCHESTRATOR_CACHE[key] = await create_orchestrator(
                    llm=llm,
                    repo_path=repo_path,
                    user_id=user_id,
                )

    return _ORCHESTRATOR_CACHE[key]


async def warm_start_cache() -> None:
    if not os.getenv("GROQ_API_KEY"):
        return

    repo_path = str(Path(__file__).resolve().parents[2])
    await get_cached_orchestrator("openai/gpt-oss-20b", repo_path, "default-user")


async def generate_chat_reply(message: str, user_id: str | None = None) -> str:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message must be a non-empty string.")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return (
            "I’m ready to help, but the Groq API key is not configured "
            "in this environment. Please set GROQ_API_KEY to enable live responses."
        )

    try:
        repo_path = str(Path(__file__).resolve().parents[2])
        resolved_user_id = user_id or "default-user"
        orchestrator = await get_cached_orchestrator(
            "openai/gpt-oss-20b",
            repo_path,
            resolved_user_id,
        )
        return await get_orchestrator_response(orchestrator, message.strip())
    except Exception:
        return (
            "I’m temporarily unable to generate a live response right now. "
            "Please try again in a moment."
        )
