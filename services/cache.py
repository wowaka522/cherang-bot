# services/cache.py
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict


@dataclass
class _Entry:
    value: Any
    expire_at: float


class TTLCache:
    """TTL 캐시 + 동일 키 동시요청 합치기(in-flight dedupe)."""

    def __init__(self, default_ttl: float = 10.0, max_items: int = 2048):
        self.default_ttl = float(default_ttl)
        self.max_items = int(max_items)
        self._store: Dict[str, _Entry] = {}
        self._inflight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    def _now(self) -> float:
        return time.time()

    def _prune(self) -> None:
        now = self._now()
        for k in list(self._store.keys()):
            if self._store[k].expire_at <= now:
                self._store.pop(k, None)

        if len(self._store) > self.max_items:
            keys = sorted(self._store.keys(), key=lambda x: self._store[x].expire_at)
            for k in keys[: max(0, len(self._store) - self.max_items)]:
                self._store.pop(k, None)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        *,
        ttl: float | None = None,
    ) -> Any:
        ttl = self.default_ttl if ttl is None else float(ttl)

        async with self._lock:
            self._prune()
            ent = self._store.get(key)
            if ent and ent.expire_at > self._now():
                return ent.value

            fut = self._inflight.get(key)
            if fut:
                return await fut

            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            self._inflight[key] = fut

        try:
            val = await factory()
            async with self._lock:
                self._store[key] = _Entry(val, self._now() + ttl)
                self._inflight.pop(key, None)
                if not fut.done():
                    fut.set_result(val)
            return val
        except Exception as e:
            async with self._lock:
                self._inflight.pop(key, None)
                if not fut.done():
                    fut.set_exception(e)
            raise


class RateLimiter:
    """키 단위 간단 레이트리밋(간격 보장)."""

    def __init__(self, interval_sec: float = 0.25):
        self.interval = float(interval_sec)
        self._next_ok: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _now(self) -> float:
        return time.time()

    async def wait(self, key: str) -> None:
        async with self._lock:
            now = self._now()
            t = self._next_ok.get(key, 0.0)
            wait_sec = max(0.0, t - now)
            self._next_ok[key] = max(t, now) + self.interval

        if wait_sec > 0:
            await asyncio.sleep(wait_sec)