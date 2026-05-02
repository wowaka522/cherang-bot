# utils/locks.py
from __future__ import annotations

import asyncio
from typing import Dict

# ✅ 키별로 Lock "하나만" 생성해서 재사용 (연타/동시 클릭 꼬임 방지 핵심)
_user_locks: Dict[int, asyncio.Lock] = {}
_guild_locks: Dict[int, asyncio.Lock] = {}
_session_locks: Dict[str, asyncio.Lock] = {}

def user_lock(user_id: int) -> asyncio.Lock:
    lock = _user_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _user_locks[user_id] = lock
    return lock

def guild_lock(guild_id: int) -> asyncio.Lock:
    lock = _guild_locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        _guild_locks[guild_id] = lock
    return lock

def session_lock(key: str) -> asyncio.Lock:
    lock = _session_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _session_locks[key] = lock
    return lock