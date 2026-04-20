"""Smart features — standup summaries, client reports, reminders, meeting prep."""

import json
from datetime import datetime, timedelta
from typing import List, Optional

from litellm import acompletion

from pm_agent.cosmos_client import CosmosDBManager
from pm_agent.graph_client import GraphCalendarClient
from pm_agent.models import TaskStatus
from utils import get_logger

logger = get_logger(__name__)


async def generate_daily_standup(db: CosmosDBManager, llm_config: dict) -> str:
    """Generate a daily standup summary across all clients and projects."""
    clients = await db.list_clients()
    all_tasks = await db.list_tasks()
    overdue = await db.get_overdue_tasks()

    # Categorize tasks
    in_progress = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]
    blocked = [t for t in all_tasks if t.status == TaskStatus.BLOCKED]

    # Tasks due this week
    now = datetime.utcnow()
    week_end = now + timedelta(days=7)
    upcoming = [
        t for t in all_tasks
        if t.due_date and now <= t.due_date <= week_end and t.status != TaskStatus.DONE
    ]

    context = {
        "date": now.strftime("%A, %B %d, %Y"),
        "total_clients": len(clients),
        "total_tasks": len(all_tasks),
        "in_progress": [{"title": t.title, "project_id": t.project_id, "assignee": t.assignee} for t in in_progress],
        "blocked": [{"title": t.title, "project_id": t.project_id, "notes": t.notes} for t in blocked],
        "overdue": [{"title": t.title, "due_date": t.due_date.isoformat() if t.due_date else None, "project_id": t.project_id} for t in overdue],
        "upcoming_this_week": [{"title": t.title, "due_date": t.due_date.isoformat() if t.due_date else None} for t in upcoming],
    }

    response = await acompletion(
        **llm_config,
        messages=[
            {"role": "system", "content": "You are a project management assistant. Generate a concise daily standup summary using emojis and structured formatting. Include: what's in progress, blockers, overdue items, and upcoming deadlines."},
            {"role": "user", "content": f"Generate today's standup summary from this data:\n{json.dumps(context, indent=2)}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


async def generate_client_report(db: CosmosDBManager, client_id: str, llm_config: dict) -> str:
    """Generate a status report for a specific client."""
    clients = await db.list_clients()
    client = next((c for c in clients if c.id == client_id), None)
    if not client:
        return f"Client with ID '{client_id}' not found."

    projects = await db.list_projects(client_id=client_id)
    all_tasks = await db.list_tasks(client_id=client_id)

    status_summary = {}
    for status in TaskStatus:
        status_summary[status.value] = len([t for t in all_tasks if t.status == status])

    overdue = [t for t in all_tasks if t.due_date and t.due_date < datetime.utcnow() and t.status != TaskStatus.DONE]

    context = {
        "client_name": client.name,
        "projects": [{"name": p.name, "status": p.status} for p in projects],
        "task_summary": status_summary,
        "total_tasks": len(all_tasks),
        "overdue_tasks": [{"title": t.title, "due_date": t.due_date.isoformat() if t.due_date else None} for t in overdue],
        "recent_completed": [
            {"title": t.title, "completed_at": t.completed_at.isoformat() if t.completed_at else None}
            for t in all_tasks if t.status == TaskStatus.DONE
        ][:10],
    }

    response = await acompletion(
        **llm_config,
        messages=[
            {"role": "system", "content": "You are a project management assistant. Generate a professional client status report with sections: Overview, Projects, Task Summary, Overdue Items, Recent Completions. Use emojis and structured formatting."},
            {"role": "user", "content": f"Generate a client status report:\n{json.dumps(context, indent=2)}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


async def get_smart_reminders(db: CosmosDBManager) -> str:
    """Get proactive reminders about overdue and upcoming tasks."""
    overdue = await db.get_overdue_tasks()
    all_tasks = await db.list_tasks()

    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)
    this_week = now + timedelta(days=7)

    due_tomorrow = [
        t for t in all_tasks
        if t.due_date and now.date() < t.due_date.date() <= tomorrow.date()
        and t.status != TaskStatus.DONE
    ]
    due_this_week = [
        t for t in all_tasks
        if t.due_date and tomorrow.date() < t.due_date.date() <= this_week.date()
        and t.status != TaskStatus.DONE
    ]
    blocked = [t for t in all_tasks if t.status == TaskStatus.BLOCKED]

    sections = []
    if overdue:
        sections.append("🚨 **Overdue Tasks:**")
        for t in overdue:
            days_late = (now - t.due_date).days if t.due_date else 0
            sections.append(f"  ⚠️ {t.title} — {days_late} days overdue (Project: {t.project_id})")

    if due_tomorrow:
        sections.append("\n⏰ **Due Tomorrow:**")
        for t in due_tomorrow:
            sections.append(f"  📋 {t.title} (Priority: {t.priority})")

    if due_this_week:
        sections.append("\n📅 **Due This Week:**")
        for t in due_this_week:
            due_str = t.due_date.strftime("%a %b %d") if t.due_date else "No date"
            sections.append(f"  📋 {t.title} — {due_str}")

    if blocked:
        sections.append("\n🚫 **Blocked Tasks:**")
        for t in blocked:
            sections.append(f"  🔴 {t.title} — {t.notes or 'No details'}")

    if not sections:
        return "✅ All clear! No overdue tasks, upcoming deadlines, or blockers."

    return "\n".join(sections)


async def generate_meeting_prep(
    db: CosmosDBManager,
    meeting_subject: str,
    client_id: Optional[str] = None,
    llm_config: dict = None,
    graph_token: Optional[str] = None,
) -> str:
    """Generate a meeting prep summary with relevant project context.

    If graph_token is provided, also pulls upcoming calendar events
    using delegated (SSO) Graph access.
    """
    context_data = {"meeting": meeting_subject}

    # Pull calendar context if we have a Graph token
    if graph_token:
        try:
            graph = GraphCalendarClient.from_user_token(graph_token)
            meetings = await graph.get_upcoming_meetings(days=3)
            matching = [m for m in meetings if meeting_subject.lower() in (m.get("subject", "") or "").lower()]
            if matching:
                context_data["calendar_event"] = matching[0]
            else:
                context_data["upcoming_meetings_count"] = len(meetings)
        except Exception as e:
            logger.warning(f"Could not fetch calendar for meeting prep: {e}")

    if client_id:
        projects = await db.list_projects(client_id=client_id)
        tasks = await db.list_tasks(client_id=client_id)
        overdue = [t for t in tasks if t.due_date and t.due_date < datetime.utcnow() and t.status != TaskStatus.DONE]
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]

        context_data.update({
            "projects": [{"name": p.name, "status": p.status} for p in projects],
            "in_progress_tasks": [{"title": t.title, "assignee": t.assignee} for t in in_progress],
            "blocked_tasks": [{"title": t.title, "notes": t.notes} for t in blocked],
            "overdue_tasks": [{"title": t.title, "due_date": t.due_date.isoformat() if t.due_date else None} for t in overdue],
        })
    else:
        all_tasks = await db.list_tasks()
        overdue = await db.get_overdue_tasks()
        context_data.update({
            "total_active_tasks": len([t for t in all_tasks if t.status != TaskStatus.DONE]),
            "overdue_count": len(overdue),
        })

    if not llm_config:
        return f"Meeting prep data:\n{json.dumps(context_data, indent=2)}"

    response = await acompletion(
        **llm_config,
        messages=[
            {"role": "system", "content": "You are a project management assistant preparing someone for a meeting. Summarize the key talking points, open items, blockers, and risks. Be concise and actionable."},
            {"role": "user", "content": f"Prepare me for this meeting:\n{json.dumps(context_data, indent=2)}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content
