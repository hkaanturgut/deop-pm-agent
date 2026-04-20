"""Microsoft Graph client for Outlook calendar and meeting integration."""

import os
from datetime import datetime, timedelta
from typing import List, Optional

from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.users.item.calendar_view.calendar_view_request_builder import CalendarViewRequestBuilder

from utils import get_logger

logger = get_logger(__name__)


class GraphCalendarClient:
    """Reads calendar events from Outlook via Microsoft Graph."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, user_email: str = None):
        self._credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        self._client = GraphServiceClient(self._credential)
        self._user_email = user_email or os.environ.get("GRAPH_USER_EMAIL", "me")

    async def get_upcoming_meetings(self, days: int = 7) -> List[dict]:
        """Get meetings for the next N days."""
        now = datetime.utcnow()
        end = now + timedelta(days=days)

        query_params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
            start_date_time=now.isoformat() + "Z",
            end_date_time=end.isoformat() + "Z",
            select=["subject", "start", "end", "organizer", "attendees", "bodyPreview", "location"],
            orderby=["start/dateTime"],
            top=50,
        )
        config = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetRequestConfiguration(
            query_parameters=query_params,
        )

        try:
            events = await self._client.users.by_user_id(self._user_email).calendar_view.get(config)
            meetings = []
            if events and events.value:
                for event in events.value:
                    meetings.append({
                        "subject": event.subject,
                        "start": event.start.date_time if event.start else None,
                        "end": event.end.date_time if event.end else None,
                        "organizer": event.organizer.email_address.name if event.organizer and event.organizer.email_address else None,
                        "attendees": [
                            a.email_address.name for a in (event.attendees or [])
                            if a.email_address
                        ],
                        "preview": event.body_preview,
                        "location": event.location.display_name if event.location else None,
                    })
            return meetings
        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            return []

    async def get_todays_meetings(self) -> List[dict]:
        """Get today's meetings."""
        return await self.get_upcoming_meetings(days=1)

    async def close(self):
        """Close the credential."""
        await self._credential.close()
