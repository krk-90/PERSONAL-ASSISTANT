from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.core.security import bearer_scheme, get_authenticated_user_id
from app.services.chat_services import generate_chat_reply

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's message")


class ChatResponse(BaseModel):
    reply: str


@router.post("/", response_model=ChatResponse)
async def chat_with_assistant(
    payload: ChatRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    user_id = get_authenticated_user_id(credentials)

    try:
        reply = await generate_chat_reply(payload.message, user_id=user_id)
        return ChatResponse(reply=reply)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
