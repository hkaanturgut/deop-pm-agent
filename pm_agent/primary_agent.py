"""Primary PM Agent — orchestrates tool calls for project management."""

import json
import os
import sys
from typing import List

from botbuilder.core import TurnContext
from litellm import acompletion
from litellm.types.utils import Choices, ModelResponse
from teams_memory import BaseScopedMemoryModule, InternalMessageInput

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from pm_agent.agent import Agent, LLMConfig
from pm_agent.cosmos_client import CosmosDBManager
from pm_agent.prompts import system_prompt
from pm_agent.tools import (
    ClientReportInput,
    CreateClientInput,
    CreateProjectInput,
    CreateTaskInput,
    GetMemorizedFields,
    GetProjectStatusInput,
    ListProjectsInput,
    ListTasksInput,
    MeetingPrepInput,
    UpdateTaskInput,
    client_report,
    create_client,
    create_project,
    create_task,
    daily_standup,
    get_memorized_fields,
    get_overdue_tasks,
    get_project_status,
    list_clients,
    list_projects,
    list_tasks,
    meeting_prep,
    smart_reminders,
    update_task,
)
from utils import get_logger

logger = get_logger(__name__)


class PMAgent(Agent):
    """Project Management Agent that handles task/project/client operations."""

    def __init__(self, llm_config: LLMConfig, db: CosmosDBManager) -> None:
        self._llm_config = llm_config
        self._db = db
        super().__init__()

    async def run(self, context: TurnContext):
        memory_module: BaseScopedMemoryModule = context.get("memory_module")
        assert memory_module

        messages = await memory_module.retrieve_conversation_history(last_minutes=5)
        llm_messages: List = [
            {"role": "system", "content": system_prompt},
            *[
                {
                    "role": "user" if message.type == "user" else "assistant",
                    "content": message.content,
                }
                for message in messages
            ],
        ]

        max_turns = 8
        for _ in range(max_turns):
            response = await acompletion(
                **self._llm_config,
                messages=llm_messages,
                tools=self._get_available_functions(),
                tool_choice="auto",
                temperature=0,
            )
            assert isinstance(response, ModelResponse)
            first_choice = response.choices[0]
            assert isinstance(first_choice, Choices)
            message = first_choice.message

            if message.tool_calls is None and message.content is not None:
                await self.send_string_message(context, message.content)
                break
            elif message.tool_calls is None:
                break

            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = tool_call.function.arguments
                res = await self._dispatch_tool(fn_name, fn_args, memory_module, context)

                if res is not None:
                    llm_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call],
                    })
                    llm_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(res),
                    })
                    await self._add_internal_message(
                        context,
                        json.dumps({"tool_call_name": fn_name, "result": res}),
                    )

    async def _dispatch_tool(
        self, fn_name: str, fn_args: str,
        memory_module: BaseScopedMemoryModule, context: TurnContext
    ) -> str | None:
        """Route tool calls to the appropriate handler."""
        dispatch = {
            "create_task": lambda: create_task(self._db, CreateTaskInput.model_validate_json(fn_args)),
            "update_task": lambda: update_task(self._db, UpdateTaskInput.model_validate_json(fn_args)),
            "list_tasks": lambda: list_tasks(self._db, ListTasksInput.model_validate_json(fn_args)),
            "get_overdue_tasks": lambda: get_overdue_tasks(self._db),
            "create_project": lambda: create_project(self._db, CreateProjectInput.model_validate_json(fn_args)),
            "list_projects": lambda: list_projects(self._db, ListProjectsInput.model_validate_json(fn_args)),
            "get_project_status": lambda: get_project_status(self._db, GetProjectStatusInput.model_validate_json(fn_args)),
            "create_client": lambda: create_client(self._db, CreateClientInput.model_validate_json(fn_args)),
            "list_clients": lambda: list_clients(self._db),
            "get_memorized_fields": lambda: get_memorized_fields(memory_module, GetMemorizedFields.model_validate_json(fn_args)),
            "daily_standup": lambda: daily_standup(self._db, self._llm_config),
            "client_report": lambda: client_report(self._db, ClientReportInput.model_validate_json(fn_args), self._llm_config),
            "smart_reminders": lambda: smart_reminders(self._db),
            "meeting_prep": lambda: meeting_prep(self._db, MeetingPrepInput.model_validate_json(fn_args), self._llm_config),
        }
        handler = dispatch.get(fn_name)
        if handler:
            return await handler()
        logger.warning(f"Unknown tool call: {fn_name}")
        return None

    def _get_available_functions(self):
        return [
            {"type": "function", "function": {"name": "create_task", "description": "Create a new task in a project", "parameters": CreateTaskInput.model_json_schema()}},
            {"type": "function", "function": {"name": "update_task", "description": "Update an existing task (status, priority, assignee, etc.)", "parameters": UpdateTaskInput.model_json_schema()}},
            {"type": "function", "function": {"name": "list_tasks", "description": "List tasks, optionally filtered by client, project, or status", "parameters": ListTasksInput.model_json_schema()}},
            {"type": "function", "function": {"name": "get_overdue_tasks", "description": "Get all tasks that are past their due date and not done", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
            {"type": "function", "function": {"name": "create_project", "description": "Create a new project for a client", "parameters": CreateProjectInput.model_json_schema()}},
            {"type": "function", "function": {"name": "list_projects", "description": "List projects, optionally filtered by client", "parameters": ListProjectsInput.model_json_schema()}},
            {"type": "function", "function": {"name": "get_project_status", "description": "Get detailed status of a project including task breakdown", "parameters": GetProjectStatusInput.model_json_schema()}},
            {"type": "function", "function": {"name": "create_client", "description": "Register a new client/organization", "parameters": CreateClientInput.model_json_schema()}},
            {"type": "function", "function": {"name": "list_clients", "description": "List all registered clients", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
            {"type": "function", "function": {"name": "get_memorized_fields", "description": "Recall previously memorized context about clients, projects, or patterns", "parameters": GetMemorizedFields.model_json_schema()}},
            {"type": "function", "function": {"name": "daily_standup", "description": "Generate a daily standup summary across all projects and clients", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
            {"type": "function", "function": {"name": "client_report", "description": "Generate a detailed status report for a specific client", "parameters": ClientReportInput.model_json_schema()}},
            {"type": "function", "function": {"name": "smart_reminders", "description": "Get proactive reminders about overdue tasks, upcoming deadlines, and blockers", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
            {"type": "function", "function": {"name": "meeting_prep", "description": "Generate a meeting preparation summary with relevant project context", "parameters": MeetingPrepInput.model_json_schema()}},
        ]

    async def _add_internal_message(self, context: TurnContext, content: str):
        conversation_ref_dict = TurnContext.get_conversation_reference(context.activity)
        memory_module: BaseScopedMemoryModule = context.get("memory_module")
        await memory_module.add_message(
            InternalMessageInput(
                content=content,
                author_id=conversation_ref_dict.bot.id,
                conversation_ref=memory_module.conversation_ref,
            )
        )
