"""Tool definitions for the PM Agent — task, project, and client management."""

import json
from typing import List, Literal, Optional

from botbuilder.core import TurnContext
from pydantic import BaseModel, Field
from teams_memory import BaseScopedMemoryModule, Topic

from pm_agent.cosmos_client import CosmosDBManager
from pm_agent.models import TaskPriority, TaskStatus

# Memory topics the PM agent cares about
topics = [
    Topic(name="Client Preferences", description="Client-specific preferences, communication style, key contacts"),
    Topic(name="Project Context", description="Current project status, goals, key milestones, blockers"),
    Topic(name="Task Patterns", description="Common task types, recurring work, typical priorities"),
    Topic(name="Meeting History", description="Past meeting outcomes, decisions made, action items"),
]


# --- Tool Input Schemas ---

class CreateTaskInput(BaseModel):
    model_config = {"json_schema_extra": {"additionalProperties": False}}
    title: str = Field(description="Task title")
    project_id: str = Field(description="Project ID this task belongs to")
    client_id: str = Field(description="Client ID this task belongs to")
    description: Optional[str] = Field(default=None, description="Task description")
    priority: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    assignee: Optional[str] = Field(default=None, description="Person assigned")
    due_date: Optional[str] = Field(default=None, description="Due date in ISO format (YYYY-MM-DD)")


class UpdateTaskInput(BaseModel):
    model_config = {"json_schema_extra": {"additionalProperties": False}}
    task_id: str = Field(description="Task ID to update")
    client_id: str = Field(description="Client ID (partition key)")
    status: Optional[Literal["todo", "in_progress", "done", "blocked"]] = None
    title: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None


class ListTasksInput(BaseModel):
    model_config = {"json_schema_extra": {"additionalProperties": False}}
    client_id: Optional[str] = Field(default=None, description="Filter by client")
    project_id: Optional[str] = Field(default=None, description="Filter by project")
    status: Optional[Literal["todo", "in_progress", "done", "blocked"]] = Field(default=None)


class CreateProjectInput(BaseModel):
    model_config = {"json_schema_extra": {"additionalProperties": False}}
    name: str = Field(description="Project name")
    client_id: str = Field(description="Client this project belongs to")
    description: Optional[str] = Field(default=None)


class ListProjectsInput(BaseModel):
    model_config = {"json_schema_extra": {"additionalProperties": False}}
    client_id: Optional[str] = Field(default=None, description="Filter by client")


class GetProjectStatusInput(BaseModel):
    model_config = {"json_schema_extra": {"additionalProperties": False}}
    project_id: str = Field(description="Project ID")
    client_id: str = Field(description="Client ID")


class CreateClientInput(BaseModel):
    model_config = {"json_schema_extra": {"additionalProperties": False}}
    name: str = Field(description="Client/company name")
    contact_name: Optional[str] = Field(default=None)
    contact_email: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class GetMemorizedFields(BaseModel):
    model_config = {"json_schema_extra": {"additionalProperties": False}}
    memory_topics: List[Literal[
        "Client Preferences", "Project Context", "Task Patterns", "Meeting History"
    ]] = Field(description="Topics to search in memory")


# --- Tool Functions ---

async def create_task(db: CosmosDBManager, input: CreateTaskInput) -> str:
    task = await db.create_task(
        title=input.title,
        project_id=input.project_id,
        client_id=input.client_id,
        description=input.description,
        priority=input.priority,
        assignee=input.assignee,
        due_date=input.due_date,
    )
    return json.dumps({"status": "created", "task": task.model_dump(mode="json")})


async def update_task(db: CosmosDBManager, input: UpdateTaskInput) -> str:
    updates = input.model_dump(exclude={"task_id", "client_id"}, exclude_none=True)
    task = await db.update_task(input.task_id, input.client_id, **updates)
    return json.dumps({"status": "updated", "task": task.model_dump(mode="json")})


async def list_tasks(db: CosmosDBManager, input: ListTasksInput) -> str:
    tasks = await db.list_tasks(
        client_id=input.client_id,
        project_id=input.project_id,
        status=input.status,
    )
    return json.dumps({"count": len(tasks), "tasks": [t.model_dump(mode="json") for t in tasks]})


async def get_overdue_tasks(db: CosmosDBManager) -> str:
    tasks = await db.get_overdue_tasks()
    return json.dumps({"count": len(tasks), "overdue_tasks": [t.model_dump(mode="json") for t in tasks]})


async def create_project(db: CosmosDBManager, input: CreateProjectInput) -> str:
    project = await db.create_project(
        name=input.name,
        client_id=input.client_id,
        description=input.description,
    )
    return json.dumps({"status": "created", "project": project.model_dump(mode="json")})


async def list_projects(db: CosmosDBManager, input: ListProjectsInput) -> str:
    projects = await db.list_projects(client_id=input.client_id)
    return json.dumps({"count": len(projects), "projects": [p.model_dump(mode="json") for p in projects]})


async def get_project_status(db: CosmosDBManager, input: GetProjectStatusInput) -> str:
    status = await db.get_project_status(input.project_id, input.client_id)
    return json.dumps({
        "project": status["project"].model_dump(mode="json"),
        "total_tasks": status["total_tasks"],
        "status_breakdown": {k.value if hasattr(k, 'value') else k: v for k, v in status["status_breakdown"].items()},
        "overdue_count": status["overdue_count"],
    })


async def create_client(db: CosmosDBManager, input: CreateClientInput) -> str:
    client = await db.create_client(
        name=input.name,
        contact_name=input.contact_name,
        contact_email=input.contact_email,
        notes=input.notes,
    )
    return json.dumps({"status": "created", "client": client.model_dump(mode="json")})


async def list_clients(db: CosmosDBManager) -> str:
    clients = await db.list_clients()
    return json.dumps({"count": len(clients), "clients": [c.model_dump(mode="json") for c in clients]})


async def get_memorized_fields(
    memory_module: BaseScopedMemoryModule, fields: GetMemorizedFields
) -> str:
    result = {}
    for topic_name in fields.memory_topics:
        topic = next((t.name for t in topics if t.name == topic_name), None)
        memories = await memory_module.search_memories(topic=topic)
        if memories:
            result[topic_name] = ", ".join([f"{m.id}. {m.content}" for m in memories])
        else:
            result[topic_name] = None
    return json.dumps(result)
