import asyncio
import logging
import time
import traceback

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.core.security import bearer_scheme, get_authenticated_user_id
from app.services import persistence
from app.services.chat_services import generate_chat_reply

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="The user's message",
    )
    conversation_id: str | None = Field(
        None,
        description="Existing conversation to append to",
    )


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str | None = None


@router.post("/", response_model=ChatResponse)
async def chat_with_assistant(
    payload: ChatRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    user_id = get_authenticated_user_id(credentials)
    text = payload.message.strip()

    conversation_id = await asyncio.to_thread(
        persistence.ensure_conversation,
        user_id,
        payload.conversation_id,
        text,
    )

    if conversation_id:
        await asyncio.to_thread(
            persistence.save_message,
            user_id,
            conversation_id,
            "user",
            text,
        )

    try:
        logger.info("=" * 60)
        logger.info("CHAT REQUEST")
        logger.info("USER ID: %s", user_id)
        logger.info("MESSAGE: %s", text)

        start_time = time.time()

        print("START generate_chat_reply")

        reply = await asyncio.wait_for(
            generate_chat_reply(
                text,
                user_id=user_id,
            ),
            timeout=120,
        )

        print("END generate_chat_reply")

        elapsed = time.time() - start_time

        logger.info(
            "CHAT SUCCESS in %.2f seconds",
            elapsed,
        )
        logger.info("=" * 60)

    except asyncio.TimeoutError:
        logger.error("CHAT TIMEOUT")
        logger.error("=" * 60)

        raise HTTPException(
            status_code=504,
            detail="Assistant request timed out after 30 seconds.",
        )

    except ValueError as exc:
        logger.error("VALUE ERROR: %s", str(exc))
        logger.error("=" * 60)

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.error("=" * 60)
        logger.error("UNEXPECTED CHAT ERROR")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)

        raise HTTPException(
            status_code=500,
            detail=f"Chat pipeline failed: {str(exc)}",
        ) from exc

    if conversation_id:
        await asyncio.to_thread(
            persistence.save_message,
            user_id,
            conversation_id,
            "assistant",
            reply,
        )

    return ChatResponse(
        reply=reply,
        conversation_id=conversation_id,
    )


@router.get("/conversations")
async def get_conversations(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    user_id = get_authenticated_user_id(credentials)

    return {
        "conversations": await asyncio.to_thread(
            persistence.list_conversations,
            user_id,
        )
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    user_id = get_authenticated_user_id(credentials)

    messages = await asyncio.to_thread(
        persistence.list_messages,
        user_id,
        conversation_id,
    )

    if messages is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return {"messages": messages}
