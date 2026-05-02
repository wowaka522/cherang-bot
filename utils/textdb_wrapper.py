# utils/textdb_wrapper.py
# TextDB 래퍼(문자열/리스트 랜덤 + 안전 포맷 뼈대)
from __future__ import annotations
import random
from typing import Any, Mapping

class Text:
    def __init__(self, textdb) -> None:
        self.db = textdb

    def get(self, key: str, default: str = "") -> str:
        val = self.db.get(key, default) if hasattr(self.db, "get") else default
        if isinstance(val, list):
            return random.choice(val) if val else default
        if isinstance(val, str):
            return val
        return default

    def fmt(self, key: str, default: str = "", **kwargs: Any) -> str:
        s = self.get(key, default)
        # 안전 포맷: 없는 변수는 그대로 둠
        for k, v in kwargs.items():
            s = s.replace("{" + k + "}", str(v))
        return s
