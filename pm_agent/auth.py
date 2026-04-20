"""Teams SSO authentication — On-Behalf-Of flow for Microsoft Graph."""

import os
from typing import Optional

import aiohttp
from botbuilder.core import TurnContext

from utils import get_logger

logger = get_logger(__name__)

# OAuth connection name configured in Azure Bot Service
SSO_CONNECTION_NAME = os.environ.get("SSO_CONNECTION_NAME", "GraphConnection")


async def get_user_token(context: TurnContext) -> Optional[str]:
    """Get a Graph token for the signed-in user via Teams SSO.

    Uses the Bot Framework token exchange: the Teams client sends an
    SSO token which the bot exchanges for a Graph access token via the
    configured OAuth connection in Azure Bot Service.
    """
    try:
        user_token_response = await context.adapter.get_user_token(
            context, SSO_CONNECTION_NAME
        )
        if user_token_response and user_token_response.token:
            return user_token_response.token
    except Exception as e:
        logger.warning(f"SSO token retrieval failed (user may need to sign in): {e}")
    return None


async def prompt_sign_in(context: TurnContext) -> None:
    """Send an OAuth sign-in card if the token isn't cached."""
    from botbuilder.core import CardFactory
    from botbuilder.schema import OAuthCard, CardAction, ActionTypes

    card = OAuthCard(
        text="Sign in to access your Outlook calendar and meetings.",
        connection_name=SSO_CONNECTION_NAME,
        buttons=[
            CardAction(
                type=ActionTypes.sign_in,
                title="Sign In",
                value=SSO_CONNECTION_NAME,
            )
        ],
    )
    await context.send_activity(
        {
            "type": "message",
            "attachments": [CardFactory.oauth_card(card)],
        }
    )


async def exchange_token_obo(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    sso_token: str,
    scopes: str = "https://graph.microsoft.com/.default",
) -> Optional[str]:
    """Exchange a Teams SSO token for a Graph token via OBO flow.

    This is the server-side on-behalf-of exchange used when the bot has
    the user's SSO JWT and needs a delegated Graph token.
    """
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "client_id": client_id,
        "client_secret": client_secret,
        "assertion": sso_token,
        "scope": scopes,
        "requested_token_use": "on_behalf_of",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("access_token")
            else:
                body = await resp.text()
                logger.error(f"OBO token exchange failed ({resp.status}): {body}")
                return None
