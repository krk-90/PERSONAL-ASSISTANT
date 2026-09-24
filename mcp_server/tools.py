from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from uuid import uuid4

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from langsmith import traceable
from supabase import Client, create_client

load_dotenv()

mcp = FastMCP(
    "task-manager",
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8001")),
)

_TASKS: dict[str, dict[str, Any]] = {}
_SUPABASE: Client | None = None
_TASK_USER_CONTEXT: ContextVar[str | None] = ContextVar(
    "task_user_context",
    default=None,
)
TASKS_TABLE = "tasks"
VALID_STATUSES = {"pending", "in_progress", "completed", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_status(value: str | None, default: str = "pending") -> str:
    normalized = (value or default).strip().lower().replace(" ", "_")
    if normalized not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{value}'. Allowed values: {sorted(VALID_STATUSES)}"
        )
    return normalized


def _normalize_priority(value: str | None, default: str = "medium") -> str:
    normalized = (value or default).strip().lower()
    if normalized not in VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority '{value}'. Allowed values: {sorted(VALID_PRIORITIES)}"
        )
    return normalized


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if tags is None:
        return []
    normalized = []
    for tag in tags:
        cleaned = str(tag).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _task_payload(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task["id"],
        "title": task["title"],
        "description": task.get("description", ""),
        "status": task["status"],
        "priority": task["priority"],
        "due_date": task.get("due_date"),
        "tags": list(task.get("tags", [])),
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
        "completed_at": task.get("completed_at"),
    }


def _get_supabase() -> Client | None:
    global _SUPABASE

    if _SUPABASE is not None:
        return _SUPABASE

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    user_id = os.getenv("TASK_USER_ID")
    if not url or not key or not user_id:
        return None

    try:
        UUID(user_id)
    except ValueError:
        return None

    _SUPABASE = create_client(url, key)
    return _SUPABASE


@contextmanager
def task_user_context(user_id: str):
    token = _TASK_USER_CONTEXT.set(user_id)
    try:
        yield
    finally:
        _TASK_USER_CONTEXT.reset(token)


def _task_user_id() -> str:
    user_id = _TASK_USER_CONTEXT.get() or os.getenv("TASK_USER_ID")
    if not user_id:
        raise RuntimeError("An authenticated user is required for task storage.")
    return user_id


@mcp.tool()
@traceable(name="mcp.add_task")
def add_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    status: str = "pending",
    due_date: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new task and return its details."""
    cleaned_title = (title or "").strip()
    if not cleaned_title:
        raise ValueError("Task title is required.")

    task_id = str(uuid4())
    now = _utc_now_iso()
    normalized_status = _normalize_status(status, default="pending")
    normalized_priority = _normalize_priority(priority, default="medium")

    task = {
        "id": task_id,
        "title": cleaned_title,
        "description": description or "",
        "status": normalized_status,
        "priority": normalized_priority,
        "due_date": due_date,
        "tags": _normalize_tags(tags),
        "created_at": now,
        "updated_at": now,
        "completed_at": now if normalized_status == "completed" else None,
    }

    supabase = _get_supabase()
    if supabase is not None:
        task["user_id"] = _task_user_id()
        response = supabase.table(TASKS_TABLE).insert(task).execute()
        if not response.data:
            raise RuntimeError("Supabase did not return the created task.")
        return _task_payload(response.data[0])

    _TASKS[task_id] = task
    return _task_payload(task)


@mcp.tool()
@traceable(name="mcp.get_tasks")
def get_tasks(status: str | None = None, priority: str | None = None) -> list[dict[str, Any]]:
    """Return all tasks, optionally filtered by status or priority."""
    supabase = _get_supabase()
    if supabase is not None:
        query = (
            supabase.table(TASKS_TABLE)
            .select("*")
            .eq("user_id", _task_user_id())
            .order("created_at")
        )
        if status is not None:
            query = query.eq("status", _normalize_status(status))
        if priority is not None:
            query = query.eq("priority", _normalize_priority(priority))
        response = query.execute()
        return [_task_payload(row) for row in response.data or []]

    tasks = list(_TASKS.values())

    if status is not None:
        tasks = [task for task in tasks if task["status"] == _normalize_status(status)]
    if priority is not None:
        tasks = [task for task in tasks if task["priority"] == _normalize_priority(priority)]

    ordered = sorted(tasks, key=lambda item: item["created_at"])
    return [_task_payload(task) for task in ordered]


@mcp.tool()
@traceable(name="mcp.get_task")
def get_task(task_id: str) -> dict[str, Any]:
    """Fetch a task by id."""
    supabase = _get_supabase()
    if supabase is not None:
        response = (
            supabase.table(TASKS_TABLE)
            .select("*")
            .eq("id", task_id)
            .eq("user_id", _task_user_id())
            .maybe_single()
            .execute()
        )
        if not response.data:
            raise ValueError(f"Task '{task_id}' not found.")
        return _task_payload(response.data)

    if task_id not in _TASKS:
        raise ValueError(f"Task '{task_id}' not found.")
    return _task_payload(_TASKS[task_id])


@mcp.tool()
@traceable(name="mcp.update_task")
def update_task(
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Update a task's fields and return the latest version."""
    supabase = _get_supabase()
    if supabase is not None:
        changes: dict[str, Any] = {"updated_at": _utc_now_iso()}
        if title is not None:
            cleaned_title = title.strip()
            if not cleaned_title:
                raise ValueError("Task title cannot be empty.")
            changes["title"] = cleaned_title
        if description is not None:
            changes["description"] = description or ""
        if priority is not None:
            changes["priority"] = _normalize_priority(priority)
        if status is not None:
            normalized_status = _normalize_status(status)
            changes["status"] = normalized_status
            changes["completed_at"] = (
                _utc_now_iso() if normalized_status == "completed" else None
            )
        if due_date is not None:
            changes["due_date"] = due_date
        if tags is not None:
            changes["tags"] = _normalize_tags(tags)

        response = (
            supabase.table(TASKS_TABLE)
            .update(changes)
            .eq("id", task_id)
            .eq("user_id", _task_user_id())
            .select("*")
            .maybe_single()
            .execute())
        if not response.data:
            raise ValueError(f"Task '{task_id}' not found.")
        return _task_payload(response.data)

    if task_id not in _TASKS:
        raise ValueError(f"Task '{task_id}' not found.")

    task = _TASKS[task_id]
    if title is not None:
        cleaned_title = title.strip()
        if not cleaned_title:
            raise ValueError("Task title cannot be empty.")
        task["title"] = cleaned_title

    if description is not None:
        task["description"] = description or ""

    if priority is not None:
        task["priority"] = _normalize_priority(priority)

    if status is not None:
        task["status"] = _normalize_status(status)
        if task["status"] == "completed" and task.get("completed_at") is None:
            task["completed_at"] = _utc_now_iso()
        elif task["status"] != "completed":
            task["completed_at"] = None

    if due_date is not None:
        task["due_date"] = due_date

    if tags is not None:
        task["tags"] = _normalize_tags(tags)

    task["updated_at"] = _utc_now_iso()
    return _task_payload(task)


@mcp.tool()
@traceable(name="mcp.complete_task")
def complete_task(task_id: str) -> dict[str, Any]:
    """Mark a task as completed."""
    return update_task(task_id, status="completed")


@mcp.tool()
@traceable(name="mcp.delete_task")
def delete_task(task_id: str) -> bool:
    """Delete a task by id. Returns True if the task existed and was removed."""
    supabase = _get_supabase()
    if supabase is not None:
        response = (
            supabase.table(TASKS_TABLE)
            .delete()
            .eq("id", task_id)
            .eq("user_id", _task_user_id())
            .execute()
        )
        return bool(response.data)

    if task_id not in _TASKS:
        return False
    del _TASKS[task_id]
    return True


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "stdio"))


__all__ = [
        "mcp",
        "add_task",
        "get_tasks",
        "get_task",
        "update_task",
        "complete_task",
        "delete_task",
    ]