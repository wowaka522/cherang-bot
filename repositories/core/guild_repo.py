# repositories/core/guild_repo.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Callable, TypeVar

from repositories.base_repo import BaseRepo
from utils.locks import guild_lock

JsonDict = Dict[str, Any]
T = TypeVar("T")

class GuildRepo(BaseRepo):
    """
    ✅ 길드 저장소
    - data/core/guilds/{guild_id}.json
    """
    def __init__(self):
        super().__init__("data/core/guilds")

    def _path(self, guild_id: int) -> Path:
        return self.base_dir / f"{guild_id}.json"

    def _default(self, guild_id: int) -> JsonDict:
        return {"id": guild_id}

    async def get(self, guild_id: int) -> JsonDict:
        return self._load_json(self._path(guild_id), default=self._default(guild_id))

    async def save(self, guild_id: int, data: JsonDict) -> None:
        async with guild_lock(guild_id):
            self._atomic_save_json(self._path(guild_id), data)

    async def update(self, guild_id: int, mutator: Callable[[JsonDict], T]) -> T:
        async with guild_lock(guild_id):
            path = self._path(guild_id)
            data = self._load_json(path, default=self._default(guild_id))
            result = mutator(data)
            self._atomic_save_json(path, data)
            return result