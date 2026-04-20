"""
Deop PM Agent - Bot configuration and middleware setup.
"""

import logging
import os
import traceback

from botbuilder.core import MemoryStorage, TurnContext
from teams import Application, ApplicationOptions, TeamsAdapter
from teams.state import TurnState
from teams_memory import (
    LLMConfig,
    MemoryMiddleware,
    MemoryModuleConfig,
    SQLiteStorageConfig,
    configure_logging,
)

from config import Config
from pm_agent.agent import LLMConfig as AgentLLMConfig
from pm_agent.cosmos_client import CosmosDBManager
from pm_agent.primary_agent import PMAgent
from pm_agent.tools import topics
from utils import get_logger

logger = get_logger(__name__)
config = Config()

# LLM configuration
memory_llm_config: dict
if config.AZURE_OPENAI_API_KEY:
    memory_llm_config = {
        "model": f"azure/{config.AZURE_OPENAI_DEPLOYMENT}",
        "api_key": config.AZURE_OPENAI_API_KEY,
        "api_base": config.AZURE_OPENAI_API_BASE,
        "api_version": config.AZURE_OPENAI_API_VERSION,
        "embedding_model": f"azure/{config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT}",
    }
elif config.OPENAI_API_KEY:
    memory_llm_config = {
        "model": config.OPENAI_MODEL_NAME,
        "api_key": config.OPENAI_API_KEY,
        "api_base": None,
        "api_version": None,
        "embedding_model": config.OPENAI_EMBEDDING_MODEL_NAME,
    }
else:
    raise ValueError("Provide either OpenAI or Azure OpenAI credentials")

agent_llm_config = AgentLLMConfig(
    model=memory_llm_config["model"],
    api_key=memory_llm_config["api_key"],
    api_base=memory_llm_config["api_base"],
    api_version=memory_llm_config["api_version"],
)

# Cosmos DB manager (initialized in app.py on startup)
cosmos_db = CosmosDBManager()

# Bot application
storage = MemoryStorage()
bot_app = Application[TurnState](
    ApplicationOptions(
        bot_app_id=config.APP_ID,
        storage=storage,
        adapter=TeamsAdapter(config),
    )
)

# Memory middleware
memory_middleware = MemoryMiddleware(
    config=MemoryModuleConfig(
        llm=LLMConfig(**memory_llm_config),
        storage=SQLiteStorageConfig(
            db_path=os.path.join(os.path.dirname(__file__), "data", "memory.db")
        ),
        timeout_seconds=120,
        buffer_size=20,
        topics=topics,
    )
)
configure_logging(logging.INFO)
bot_app.adapter.use(memory_middleware)


@bot_app.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, state: TurnState):
    await context.send_activity(
        "👋 Hello! I'm the **Deop PM Agent** — your AI project management assistant.\n\n"
        "I can help you with:\n"
        "• 📋 **Task management** — create, update, and track tasks\n"
        "• 📊 **Project status** — check progress across clients\n"
        "• 📅 **Meeting prep** — get context before meetings\n"
        "• 📝 **Standup summaries** — daily updates across all projects\n"
        "• ⏰ **Smart reminders** — overdue tasks and deadlines\n\n"
        "How can I help you today?"
    )
    return True


@bot_app.activity("message")
async def on_message(context: TurnContext, state: TurnState):
    from pm_agent.auth import get_user_token

    # Try to get a delegated Graph token via Teams SSO
    user_graph_token = await get_user_token(context)

    pm_agent = PMAgent(agent_llm_config, cosmos_db, graph_token=user_graph_token)
    await pm_agent.run(context)
    return True


@bot_app.error
async def on_error(context: TurnContext, error: Exception):
    logger.error(f"\n [on_turn_error] unhandled error: {error}")
    traceback.print_exc()
    await context.send_activity("⚠️ The bot encountered an error. Please try again.")
