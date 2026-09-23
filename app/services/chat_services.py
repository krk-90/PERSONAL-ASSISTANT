import asyncio
import os
from pathlib import Path

from agent.graph.orchestrator.orchestrator import create_orchestrator, get_orchestrator_response
from llm_gateway.provider.groq_llm import get_model


def generate_chat_reply(message: str, user_id: str | None = None) -> str:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message must be a non-empty string.")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return (
            "I’m ready to help, but the Groq API key is not configured "
            "in this environment. Please set GROQ_API_KEY to enable live responses."
        )

    try:
        llm = get_model("openai/gpt-oss-20b")
        repo_path = str(Path(__file__).resolve().parents[2])
        resolved_user_id = user_id or "default-user"

        async def _run_orchestrator() -> str:
            orchestrator = await create_orchestrator(
                llm=llm,
                repo_path=repo_path,
                user_id=resolved_user_id,
            )
            return await get_orchestrator_response(orchestrator, message.strip())

        return asyncio.run(_run_orchestrator())
    except Exception:
        return (
            "I’m temporarily unable to generate a live response right now. "
            "Please try again in a moment."
        )
