# repositories/core/user_repo.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Callable, TypeVar

from repositories.base_repo import BaseRepo
from utils.locks import user_lock

JsonDict = Dict[str, Any]
T = TypeVar("T")

class UserRepo(BaseRepo):
    """
    ✅ 유저 저장소
    - data/core/users/{user_id}.json
    """
    def __init__(self):
        super().__init__("data/core/users")

    def _path(self, user_id: int) -> Path:
        return self.base_dir / f"{user_id}.json"

    def _default(self, user_id: int) -> JsonDict:
        return {"id": user_id}

    async def get(self, user_id: int) -> JsonDict:
        return self._load_json(self._path(user_id), default=self._default(user_id))

    async def save(self, user_id: int, data: JsonDict) -> None:
        async with user_lock(user_id):
            self._atomic_save_json(self._path(user_id), data)

    async def update(self, user_id: int, mutator: Callable[[JsonDict], T]) -> T:
        """
        ✅ 연타/동시 클릭 안전 패턴:
        - lock -> load -> mutate -> save
        """
        async with user_lock(user_id):
            path = self._path(user_id)
            data = self._load_json(path, default=self._default(user_id))
            result = mutator(data)
            self._atomic_save_json(path, data)
            return result