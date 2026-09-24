"""Persist conversations and messages to Supabase (service-role client, ownership checked in code)."""
from __future__ import annotations

import logging
import os
from typing import Any

from supabase import Client, create_client

logger = logging.getLogger(__name__)
_CLIENT: Client | None = None


def _client() -> Client | None:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Chat persistence disabled: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
        return None
    _CLIENT = create_client(url, key)
    return _CLIENT


def _owns(client: Client, conversation_id: str, user_id: str) -> bool:
    res = (
        client.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def ensure_conversation(user_id: str, conversation_id: str | None, first_message: str) -> str | None:
    """Return a conversation id owned by user_id, creating one if needed. None if persistence failed."""
    client = _client()
    if client is None:
        return None
    try:
        if conversation_id and _owns(client, conversation_id, user_id):
            return conversation_id
        title = first_message.strip().replace("\n", " ")[:60] or "New Conversation"
        res = client.table("conversations").insert({"user_id": user_id, "title": title}).execute()
        return res.data[0]["id"]
    except Exception:
        logger.exception("Failed to create/verify conversation")
        return None


def save_message(user_id: str, conversation_id: str, role: str, content: str,
                 metadata: dict[str, Any] | None = None) -> None:
    client = _client()
    if client is None or not conversation_id:
        return
    try:
        client.table("messages").insert({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }).execute()
        client.table("conversations").update({"updated_at": "now()"}).eq("id", conversation_id).eq("user_id", user_id).execute()
    except Exception:
        logger.exception("Failed to save %s message", role)


def list_conversations(user_id: str, limit: int = 50) -> list[dict]:
    client = _client()
    if client is None:
        return []
    res = (
        client.table("conversations")
        .select("id,title,created_at,updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def list_messages(user_id: str, conversation_id: str, limit: int = 500) -> list[dict] | None:
    """Messages for a conversation, or None if it doesn't belong to the user."""
    client = _client()
    if client is None or not _owns(client, conversation_id, user_id):
        return None
    res = (
        client.table("messages")
        .select("id,role,content,created_at")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .order("created_at")
        .limit(limit)
        .execute()
    )
    return res.data or []
