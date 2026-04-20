"""Adaptive Card templates for rich Teams UI responses."""

import json
from typing import List, Optional
from pm_agent.models import Task, Project, Client, TaskStatus


def task_card(task: dict) -> dict:
    """Render a single task as an Adaptive Card."""
    status_emoji = {
        "todo": "📋", "in_progress": "🔄", "done": "✅", "blocked": "🚫"
    }
    priority_color = {
        "low": "good", "medium": "default", "high": "warning", "critical": "attention"
    }
    status = task.get("status", "todo")
    priority = task.get("priority", "medium")

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "TextBlock",
                "text": f"{status_emoji.get(status, '📋')} {task.get('title', 'Untitled')}",
                "weight": "bolder",
                "size": "medium",
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Status", "value": status.replace("_", " ").title()},
                    {"title": "Priority", "value": priority.title()},
                    {"title": "Assignee", "value": task.get("assignee") or "Unassigned"},
                    {"title": "Due Date", "value": task.get("due_date", "Not set")},
                    {"title": "Project", "value": task.get("project_id", "N/A")},
                ],
            },
        ],
    }


def task_list_card(tasks: List[dict], title: str = "Tasks") -> dict:
    """Render a list of tasks as an Adaptive Card."""
    status_emoji = {
        "todo": "📋", "in_progress": "🔄", "done": "✅", "blocked": "🚫"
    }

    rows = []
    for t in tasks[:20]:  # Limit to 20 for readability
        status = t.get("status", "todo")
        emoji = status_emoji.get(status, "📋")
        due = t.get("due_date", "No date")
        if due and "T" in str(due):
            due = str(due).split("T")[0]
        rows.append({
            "type": "ColumnSet",
            "columns": [
                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": emoji}]},
                {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": t.get("title", "Untitled"), "wrap": True}]},
                {"type": "Column", "width": "auto", "items": [{"type": "TextBlock", "text": str(due), "isSubtle": True}]},
            ],
        })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": title, "weight": "bolder", "size": "large"},
            {"type": "TextBlock", "text": f"{len(tasks)} task(s)", "isSubtle": True, "spacing": "none"},
            *rows,
        ],
    }


def project_status_card(project: dict, status_breakdown: dict, overdue_count: int, total_tasks: int) -> dict:
    """Render a project status dashboard as an Adaptive Card."""
    facts = [
        {"title": "Total Tasks", "value": str(total_tasks)},
    ]
    emoji_map = {"todo": "📋", "in_progress": "🔄", "done": "✅", "blocked": "🚫"}
    for status, count in status_breakdown.items():
        emoji = emoji_map.get(status, "")
        facts.append({"title": f"{emoji} {status.replace('_', ' ').title()}", "value": str(count)})

    if overdue_count > 0:
        facts.append({"title": "⚠️ Overdue", "value": str(overdue_count)})

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": f"📊 {project.get('name', 'Project')}", "weight": "bolder", "size": "large"},
            {"type": "TextBlock", "text": f"Client: {project.get('client_id', 'N/A')}", "isSubtle": True, "spacing": "none"},
            {"type": "FactSet", "facts": facts},
        ],
    }


def create_task_form_card() -> dict:
    """Render a task creation form as an Adaptive Card."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": "📝 Create New Task", "weight": "bolder", "size": "large"},
            {"type": "Input.Text", "id": "title", "label": "Task Title", "isRequired": True, "placeholder": "Enter task title..."},
            {"type": "Input.Text", "id": "description", "label": "Description", "isMultiline": True, "placeholder": "Optional description..."},
            {"type": "Input.Text", "id": "project_id", "label": "Project ID", "isRequired": True, "placeholder": "Project ID"},
            {"type": "Input.Text", "id": "client_id", "label": "Client ID", "isRequired": True, "placeholder": "Client ID"},
            {
                "type": "Input.ChoiceSet",
                "id": "priority",
                "label": "Priority",
                "value": "medium",
                "choices": [
                    {"title": "🟢 Low", "value": "low"},
                    {"title": "🟡 Medium", "value": "medium"},
                    {"title": "🟠 High", "value": "high"},
                    {"title": "🔴 Critical", "value": "critical"},
                ],
            },
            {"type": "Input.Text", "id": "assignee", "label": "Assignee", "placeholder": "Optional assignee..."},
            {"type": "Input.Date", "id": "due_date", "label": "Due Date"},
        ],
        "actions": [
            {"type": "Action.Submit", "title": "Create Task", "data": {"action": "create_task"}},
        ],
    }


def meeting_prep_card(meeting_subject: str, prep_content: str) -> dict:
    """Render a meeting prep summary as an Adaptive Card."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": f"📅 Meeting Prep: {meeting_subject}", "weight": "bolder", "size": "large"},
            {"type": "TextBlock", "text": prep_content, "wrap": True},
        ],
    }
