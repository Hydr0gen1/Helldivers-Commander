from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> object | None: ...

    @abstractmethod
    async def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


@dataclass(slots=True)
class CacheEntry(Generic[T]):
    value: T
    expires_at: float | None


class InProcTTLCache(Cache):
    def __init__(self) -> None:
        self._items: dict[str, CacheEntry[object]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> object | None:
        async with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expires_at is not None and entry.expires_at <= time.monotonic():
                self._items.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        expires_at = None if ttl_seconds is None else time.monotonic() + ttl_seconds
        async with self._lock:
            self._items[key] = CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._items.pop(key, None)


class RedisCache(Cache):
    def __init__(self, url: str) -> None:
        raise NotImplementedError("Redis cache is reserved for multi-worker deployments; use blank REDIS_URL for M1.")
