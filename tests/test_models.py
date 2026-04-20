"""Tests for PM Agent data models."""

from datetime import datetime
from pm_agent.models import Task, Project, Client, TaskStatus, TaskPriority


def test_task_creation():
    task = Task(
        id="t1",
        title="Fix login bug",
        project_id="p1",
        client_id="c1",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
    )
    assert task.id == "t1"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH
    assert task.partition_key == "c1"


def test_task_default_values():
    task = Task(id="t2", title="Test", project_id="p1", client_id="c1")
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.MEDIUM
    assert task.assignee is None
    assert task.due_date is None
    assert task.tags == []


def test_project_creation():
    project = Project(id="p1", name="Website Redesign", client_id="c1")
    assert project.name == "Website Redesign"
    assert project.status == "active"
    assert project.partition_key == "c1"


def test_client_creation():
    client = Client(id="c1", name="Acme Corp", contact_name="John Doe")
    assert client.name == "Acme Corp"
    assert client.contact_name == "John Doe"
    assert client.partition_key == "c1"


def test_task_status_enum():
    assert TaskStatus.TODO == "todo"
    assert TaskStatus.IN_PROGRESS == "in_progress"
    assert TaskStatus.DONE == "done"
    assert TaskStatus.BLOCKED == "blocked"


def test_task_serialization():
    task = Task(id="t1", title="Test", project_id="p1", client_id="c1")
    data = task.model_dump(mode="json")
    assert data["id"] == "t1"
    assert data["status"] == "todo"
    assert "created_at" in data
