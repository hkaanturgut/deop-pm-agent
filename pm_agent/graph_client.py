"""Microsoft Graph client for Outlook calendar and meeting integration.

Supports two auth modes:
  1. **Delegated (SSO)** — pass a user access_token from Teams SSO / OBO flow.
     The client calls `/me/calendarView` so no user_email is needed.
  2. **App-only** — pass tenant_id, client_id, client_secret.
     The client calls `/users/{email}/calendarView`.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional

from azure.identity.aio import ClientSecretCredential
from kiota_abstractions.authentication import AccessTokenProvider, AllowedHostsValidator
from kiota_authentication_azure.azure_identity_access_token_provider import AzureIdentityAccessTokenProvider
from msgraph import GraphServiceClient
from msgraph.generated.users.item.calendar_view.calendar_view_request_builder import CalendarViewRequestBuilder

from utils import get_logger

logger = get_logger(__name__)


class _StaticTokenProvider(AccessTokenProvider):
    """Wraps a pre-fetched access token for the Graph SDK."""

    def __init__(self, token: str):
        self._token = token
        self._hosts = AllowedHostsValidator(["graph.microsoft.com"])

    async def get_authorization_token(self, uri: str, additional_authentication_context: dict = None) -> str:
        return self._token

    def get_allowed_hosts_validator(self) -> AllowedHostsValidator:
        return self._hosts


class GraphCalendarClient:
    """Reads calendar events from Outlook via Microsoft Graph.

    Usage:
        # Delegated (SSO) — preferred in Teams context
        client = GraphCalendarClient.from_user_token(access_token)

        # App-only fallback
        client = GraphCalendarClient(tenant_id, client_id, client_secret, user_email)
    """

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, user_email: str = None):
        self._credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        self._client = GraphServiceClient(self._credential)
        self._user_email = user_email or os.environ.get("GRAPH_USER_EMAIL", "me")
        self._delegated = False

    @classmethod
    def from_user_token(cls, access_token: str) -> "GraphCalendarClient":
        """Create a client using a delegated user token (Teams SSO)."""
        from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider
        from msgraph import GraphRequestAdapter

        instance = cls.__new__(cls)
        instance._credential = None
        token_provider = _StaticTokenProvider(access_token)
        auth_provider = AzureIdentityAuthenticationProvider(credential=None, scopes=[])
        # Override the token provider
        auth_provider.access_token_provider = token_provider
        adapter = GraphRequestAdapter(auth_provider)
        instance._client = GraphServiceClient(request_adapter=adapter)
        instance._user_email = "me"
        instance._delegated = True
        return instance

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
