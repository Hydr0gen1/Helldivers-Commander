from __future__ import annotations

from fastapi import Request

from app.cache import Cache
from app.clients.upstream import UpstreamClient
from app.briefing.llm import BriefingGenerator


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


def get_upstream(request: Request) -> UpstreamClient:
    return request.app.state.upstream


def get_briefing_generator(request: Request) -> BriefingGenerator:
    return request.app.state.briefing_generator
