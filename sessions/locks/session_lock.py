# sessions/locks/session_lock.py
# 유저/길드 세션 락 (기본 뼈대)
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class UserSession:
    lock: asyncio.Lock
    message_id: Optional[int] = None

class SessionManager:
    def __init__(self) -> None:
        self._user: Dict[int, UserSession] = {}

    def get_user_session(self, user_id: int) -> UserSession:
        if user_id not in self._user:
            self._user[user_id] = UserSession(lock=asyncio.Lock())
        return self._user[user_id]
