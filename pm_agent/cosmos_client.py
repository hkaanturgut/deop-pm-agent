"""Cosmos DB client for managing tasks, projects, and clients."""

import os
import uuid
from datetime import datetime
from typing import List, Optional

from azure.cosmos.aio import CosmosClient, ContainerProxy
from azure.identity.aio import DefaultAzureCredential

from pm_agent.models import Client, Project, Task, TaskStatus


class CosmosDBManager:
    """Manages CRUD operations against Cosmos DB for PM data."""

    def __init__(self):
        self._client: Optional[CosmosClient] = None
        self._db = None
        self._tasks_container: Optional[ContainerProxy] = None
        self._projects_container: Optional[ContainerProxy] = None
        self._clients_container: Optional[ContainerProxy] = None

    async def initialize(self):
        """Initialize Cosmos DB connection using Managed Identity or connection string."""
        endpoint = os.environ.get("COSMOS_ENDPOINT")
        key = os.environ.get("COSMOS_KEY")
        database_name = os.environ.get("COSMOS_DATABASE", "deop-pm-db")

        if endpoint and not key:
            credential = DefaultAzureCredential()
            self._client = CosmosClient(endpoint, credential=credential)
        elif endpoint and key:
            self._client = CosmosClient(endpoint, credential=key)
        else:
            raise ValueError("COSMOS_ENDPOINT must be set")

        self._db = self._client.get_database_client(database_name)
        self._tasks_container = self._db.get_container_client("tasks")
        self._projects_container = self._db.get_container_client("projects")
        self._clients_container = self._db.get_container_client("clients")

    async def close(self):
        """Close the Cosmos DB client."""
        if self._client:
            await self._client.close()

    # --- Tasks ---

    async def create_task(
        self,
        title: str,
        project_id: str,
        client_id: str,
        description: Optional[str] = None,
        priority: str = "medium",
        assignee: Optional[str] = None,
        due_date: Optional[str] = None,
    ) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            project_id=project_id,
            client_id=client_id,
            priority=priority,
            assignee=assignee,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
        )
        await self._tasks_container.create_item(
            body=task.model_dump(mode="json"),
            partition_key=task.partition_key,
        )
        return task

    async def update_task(self, task_id: str, client_id: str, **updates) -> Task:
        item = await self._tasks_container.read_item(task_id, partition_key=client_id)
        for key, value in updates.items():
            if key in item and value is not None:
                item[key] = value
        item["updated_at"] = datetime.utcnow().isoformat()
        if updates.get("status") == TaskStatus.DONE:
            item["completed_at"] = datetime.utcnow().isoformat()
        await self._tasks_container.replace_item(task_id, item, partition_key=client_id)
        return Task(**item)

    async def list_tasks(
        self,
        client_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Task]:
        conditions = ["1=1"]
        params = []
        if client_id:
            conditions.append("c.client_id = @client_id")
            params.append({"name": "@client_id", "value": client_id})
        if project_id:
            conditions.append("c.project_id = @project_id")
            params.append({"name": "@project_id", "value": project_id})
        if status:
            conditions.append("c.status = @status")
            params.append({"name": "@status", "value": status})

        query = f"SELECT * FROM c WHERE {' AND '.join(conditions)} ORDER BY c.due_date ASC"
        items = self._tasks_container.query_items(query=query, parameters=params)
        return [Task(**item) async for item in items]

    async def get_overdue_tasks(self) -> List[Task]:
        now = datetime.utcnow().isoformat()
        query = (
            "SELECT * FROM c WHERE c.due_date < @now "
            "AND c.status != 'done' ORDER BY c.due_date ASC"
        )
        items = self._tasks_container.query_items(
            query=query, parameters=[{"name": "@now", "value": now}]
        )
        return [Task(**item) async for item in items]

    # --- Projects ---

    async def create_project(
        self,
        name: str,
        client_id: str,
        description: Optional[str] = None,
    ) -> Project:
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            client_id=client_id,
            description=description,
        )
        await self._projects_container.create_item(
            body=project.model_dump(mode="json"),
            partition_key=project.partition_key,
        )
        return project

    async def list_projects(self, client_id: Optional[str] = None) -> List[Project]:
        if client_id:
            query = "SELECT * FROM c WHERE c.client_id = @cid"
            params = [{"name": "@cid", "value": client_id}]
        else:
            query = "SELECT * FROM c"
            params = []
        items = self._projects_container.query_items(query=query, parameters=params)
        return [Project(**item) async for item in items]

    async def get_project_status(self, project_id: str, client_id: str) -> dict:
        project = await self._projects_container.read_item(project_id, partition_key=client_id)
        tasks = await self.list_tasks(project_id=project_id, client_id=client_id)
        status_counts = {}
        for task in tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        overdue = [t for t in tasks if t.due_date and t.due_date < datetime.utcnow() and t.status != TaskStatus.DONE]
        return {
            "project": Project(**project),
            "total_tasks": len(tasks),
            "status_breakdown": status_counts,
            "overdue_count": len(overdue),
            "tasks": tasks,
        }

    # --- Clients ---

    async def create_client(
        self,
        name: str,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Client:
        client = Client(
            id=str(uuid.uuid4()),
            name=name,
            contact_name=contact_name,
            contact_email=contact_email,
            notes=notes,
        )
        await self._clients_container.create_item(
            body=client.model_dump(mode="json"),
            partition_key=client.partition_key,
        )
        return client

    async def list_clients(self) -> List[Client]:
        query = "SELECT * FROM c"
        items = self._clients_container.query_items(query=query, parameters=[])
        return [Client(**item) async for item in items]
