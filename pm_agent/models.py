"""Data models for Cosmos DB documents — clients, projects, and tasks."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(BaseModel):
    """A task within a project."""
    id: str = Field(description="Unique task ID")
    title: str = Field(description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    assignee: Optional[str] = Field(default=None, description="Person assigned to this task")
    due_date: Optional[datetime] = Field(default=None, description="Task deadline")
    project_id: str = Field(description="Parent project ID")
    client_id: str = Field(description="Parent client ID")
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    # Cosmos DB partition key
    @property
    def partition_key(self) -> str:
        return self.client_id


class Project(BaseModel):
    """A project belonging to a client."""
    id: str = Field(description="Unique project ID")
    name: str = Field(description="Project name")
    description: Optional[str] = Field(default=None)
    client_id: str = Field(description="Parent client ID")
    status: str = Field(default="active", description="active, completed, on_hold")
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def partition_key(self) -> str:
        return self.client_id


class Client(BaseModel):
    """A client/organization that Kaan works with."""
    id: str = Field(description="Unique client ID")
    name: str = Field(description="Client/company name")
    contact_name: Optional[str] = Field(default=None, description="Primary contact person")
    contact_email: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def partition_key(self) -> str:
        return self.id
