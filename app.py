"""
Deop PM Agent - Application entry point.
"""

import os
from http import HTTPStatus

from aiohttp import web
from botbuilder.core.integration import aiohttp_error_middleware

from bot import bot_app, cosmos_db, memory_middleware
from config import Config
from utils import get_logger

routes = web.RouteTableDef()
logger = get_logger(__name__)


@routes.post("/api/messages")
async def on_messages(req: web.Request) -> web.Response:
    res = await bot_app.process(req)
    if res is not None:
        return res
    return web.Response(status=HTTPStatus.OK)


@routes.get("/api/memories")
async def get_memories(request: web.Request) -> web.Response:
    user_id = request.query.get("userId")
    if not user_id:
        return web.Response(status=HTTPStatus.BAD_REQUEST, text="Missing userId parameter")
    memories = await memory_middleware.memory_module.get_memories(user_id=user_id)
    return web.json_response(
        [memory.model_dump(mode="json", by_alias=True) for memory in memories]
    )


@routes.get("/api/health")
async def health_check(_request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "agent": "deop-pm-agent"})


app = web.Application(middlewares=[aiohttp_error_middleware])
app.add_routes(routes)

app.router.add_static(
    "/memoriesTab", os.path.join(os.path.dirname(__file__), "public/memoriesTab")
)


async def on_startup(_app: web.Application):
    await memory_middleware.memory_module.listen()
    await cosmos_db.initialize()
    logger.info("✅ Deop PM Agent started — memory & Cosmos DB initialized")


async def on_shutdown(_app: web.Application):
    await memory_middleware.memory_module.shutdown()
    await cosmos_db.close()
    logger.info("🛑 Deop PM Agent shutdown complete")


if __name__ == "__main__":
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="localhost", port=Config.PORT)
