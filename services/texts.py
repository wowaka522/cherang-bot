# services/texts.py
from __future__ import annotations

import json
import os
from typing import Any


class Texts:
    """
    data/text 아래 json들을 로드해서 key로 문자열을 꺼내는 간단 텍스트 서비스.
    - 키 없으면 key 그대로 반환(디버깅)
    - format(**kwargs) 지원
    """

    def __init__(self, root: str = "data/text"):
        self.root = root
        self._data: dict[str, str] = {}

    def load_file(self, rel_path: str) -> None:
        path = os.path.join(self.root, rel_path)
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict):
            self._data.update(obj)

    def load_folder(self, rel_folder: str) -> None:
        folder = os.path.join(self.root, rel_folder)
        if not os.path.isdir(folder):
            return

        for fn in os.listdir(folder):
            if not fn.endswith(".json"):
                continue
            self.load_file(os.path.join(rel_folder, fn))

    def t(self, key: str, **kwargs: Any) -> str:
        s = self._data.get(key, key)
        if kwargs:
            try:
                return s.format(**kwargs)
            except Exception:
                return s
        return s