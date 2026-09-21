from mcp_server.tools import (
    add_task,
    complete_task,
    delete_task,
    get_tasks,
    update_task,
)


def test_create_and_list_tasks():
    task = add_task("Plan sprint", "Define sprint goals", priority="high")

    assert task["title"] == "Plan sprint"
    assert task["status"] == "pending"
    assert task["priority"] == "high"

    tasks = get_tasks()
    assert any(item["id"] == task["id"] for item in tasks)


def test_update_and_complete_task():
    task = add_task("Draft release notes", "Write notes for v2")

    updated = update_task(task["id"], status="in_progress", priority="medium")
    assert updated["status"] == "in_progress"
    assert updated["priority"] == "medium"

    completed = complete_task(task["id"])
    assert completed["status"] == "completed"


def test_delete_task():
    task = add_task("Clean up backlog", "Archive old work")
    assert delete_task(task["id"]) is True
    assert all(item["id"] != task["id"] for item in get_tasks())
