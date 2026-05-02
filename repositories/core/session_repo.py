# repositories/core/session_repo.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Callable, TypeVar

from repositories.base_repo import BaseRepo
from utils.locks import session_lock

JsonDict = Dict[str, Any]
T = TypeVar("T")

class SessionRepo(BaseRepo):
    """
    ✅ 세션 저장소
    - data/core/sessions/{key}.json
    key 예시:
      - "channel:123"
      - "user:456"
      - "guild:789"
      - "fishing:channel:123"
    """
    def __init__(self):
        super().__init__("data/core/sessions")

    def _safe_name(self, key: str) -> str:
        # 파일명 안전 처리
        return key.replace("/", "_").replace("\\", "_").replace("..", "_")

    def _path(self, key: str) -> Path:
        return self.base_dir / f"{self._safe_name(key)}.json"

    def _default(self, key: str) -> JsonDict:
        return {"key": key}

    async def get(self, key: str) -> JsonDict:
        return self._load_json(self._path(key), default=self._default(key))

    async def save(self, key: str, data: JsonDict) -> None:
        async with session_lock(key):
            self._atomic_save_json(self._path(key), data)

    async def delete(self, key: str) -> None:
        async with session_lock(key):
            path = self._path(key)
            if path.exists():
                path.unlink()

    async def update(self, key: str, mutator: Callable[[JsonDict], T]) -> T:
        async with session_lock(key):
            path = self._path(key)
            data = self._load_json(path, default=self._default(key))
            result = mutator(data)
            self._atomic_save_json(path, data)
            return result