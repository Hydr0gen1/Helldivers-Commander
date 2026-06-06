from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_briefing, routes_dispatches, routes_graph, routes_health, routes_orders, routes_planets, routes_war, stream
from app.briefing.llm import BriefingGenerator
from app.cache import InProcTTLCache, RedisCache
from app.clients.base import UpstreamHTTPClient
from app.clients.sources.community import CommunitySource
from app.clients.upstream import UpstreamClient
from app.config import settings
from app.ingest.worker import IngestWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    cache = RedisCache(settings.redis_url) if settings.redis_url else InProcTTLCache()
    http = UpstreamHTTPClient(settings)
    community = CommunitySource(http, settings)
    upstream = UpstreamClient(community)
    worker = IngestWorker(upstream, cache, settings)
    app.state.cache = cache
    app.state.http = http
    app.state.upstream = upstream
    app.state.worker = worker
    app.state.briefing_generator = BriefingGenerator()
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()
        await http.close()


def create_app() -> FastAPI:
    app = FastAPI(title="WarDesk", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            content = exc.detail
        else:
            content = {"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error path=%s error=%r", request.url.path, exc)
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error"}})

    app.include_router(routes_war.router)
    app.include_router(routes_planets.router)
    app.include_router(routes_orders.router)
    app.include_router(routes_dispatches.router)
    app.include_router(routes_graph.router)
    app.include_router(routes_briefing.router)
    app.include_router(routes_health.router)
    app.include_router(stream.router)
    return app


app = create_app()
