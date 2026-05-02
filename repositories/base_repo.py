# repositories/base_repo.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

JsonDict = Dict[str, Any]

class BaseRepo:
    """
    ✅ Repo 공통 기반:
    - JSON load
    - Atomic save (tmp -> os.replace)
    - ensure dir
    """

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_parent(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def _load_json(self, path: Path, default: Optional[JsonDict] = None) -> JsonDict:
        if not path.exists():
            return default or {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            # dict가 아니면 안전하게 default로
            return default or {}
        except Exception:
            # 파일이 깨졌거나 JSON 에러면 default로 복구 (로그는 상위에서 처리해도 됨)
            return default or {}

    def _atomic_save_json(self, path: Path, data: JsonDict) -> None:
        """
        ✅ 원자적 저장:
        - 임시 파일에 저장 후 os.replace로 교체
        """
        self._ensure_parent(path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)