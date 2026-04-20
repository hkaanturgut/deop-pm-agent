"""Deop PM Agent - Configuration."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot Configuration"""

    PORT = 3978
    APP_ID = os.environ.get("BOT_ID", "")
    APP_PASSWORD = os.environ.get("BOT_PASSWORD", "")

    # Azure OpenAI
    AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", None)
    AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", None)
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", None)
    AZURE_OPENAI_API_BASE = os.environ.get("AZURE_OPENAI_API_BASE", None)
    AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", None)

    # OpenAI (alternative)
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)
    OPENAI_MODEL_NAME = os.environ.get("OPENAI_MODEL_NAME", None)
    OPENAI_EMBEDDING_MODEL_NAME = os.environ.get("OPENAI_EMBEDDING_MODEL_NAME", None)

    # Cosmos DB
    COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT", None)
    COSMOS_KEY = os.environ.get("COSMOS_KEY", None)
    COSMOS_DATABASE = os.environ.get("COSMOS_DATABASE", "deop-pm-db")

    # Microsoft Graph (for calendar integration)
    GRAPH_CLIENT_ID = os.environ.get("GRAPH_CLIENT_ID", None)
    GRAPH_CLIENT_SECRET = os.environ.get("GRAPH_CLIENT_SECRET", None)
    GRAPH_TENANT_ID = os.environ.get("GRAPH_TENANT_ID", None)
