# services/http_client.py
from __future__ import annotations

import aiohttp
import asyncio
from typing import Any, Optional


class HttpClient:
    """봇 전체에서 공유하는 aiohttp 세션 1개"""

    def __init__(self, *, timeout_sec: int = 10):
        self._timeout = aiohttp.ClientTimeout(total=timeout_sec)
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._session and not self._session.closed:
                return
            self._session = aiohttp.ClientSession(timeout=self._timeout)

    async def close(self) -> None:
        async with self._lock:
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            raise RuntimeError("HttpClient session is not started. Call await http_client.start() first.")
        return self._session

    async def get_json(self, url: str, *, params: dict | None = None, headers: dict | None = None) -> Any:
        async with self.session.get(url, params=params, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()