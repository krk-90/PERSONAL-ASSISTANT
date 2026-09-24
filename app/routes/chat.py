import asyncio
import time
import traceback

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.core.security import bearer_scheme, get_authenticated_user_id
from app.services import persistence
from app.services.chat_services import generate_chat_reply

router = APIRouter(prefix="/chat", tags=["chat"])


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
        print("=" * 60)
        print("CHAT REQUEST")
        print(f"user_id={user_id}")
        print(f"message={text}")

        start_time = time.time()

        reply = await asyncio.wait_for(
            generate_chat_reply(
                text,
                user_id=user_id,
            ),
            timeout=30,
        )

        elapsed = time.time() - start_time

        print(f"CHAT SUCCESS ({elapsed:.2f}s)")
        print("=" * 60)

    except asyncio.TimeoutError:
        print("CHAT TIMEOUT")
        print("=" * 60)

        raise HTTPException(
            status_code=504,
            detail="Assistant request timed out after 30 seconds.",
        )

    except ValueError as exc:
        print("VALUE ERROR")
        print(str(exc))
        print("=" * 60)

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print("=" * 60)
        print("UNEXPECTED CHAT ERROR")
        print(traceback.format_exc())
        print("=" * 60)

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