# services/ffxiv/item_index.py
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple


_ws_re = re.compile(r"\s+")
_non_alnum_re = re.compile(r"[^0-9a-z가-힣]+")


def _norm(s: str) -> str:
    """
    검색용 정규화:
    - 소문자
    - 공백 제거
    - 특수문자 제거(한글/영문/숫자만 남김)
    """
    s = (s or "").strip().lower()
    s = _ws_re.sub("", s)
    s = _non_alnum_re.sub("", s)
    return s


@dataclass(frozen=True)
class ItemEntry:
    item_id: int
    name: str
    icon: str
    desc: str
    category: str
    name_norm: str


class ItemIndex:
    """
    items.json 단일 소스 인덱서
    - load() 한 번만
    - search(query) -> (item_id, real_name, similar_names)
    - get(item_id) -> ItemEntry | None
    """

    def __init__(self, json_path: str = "data/ffxiv/market/items.json"):
        self.json_path = json_path
        self._loaded = False

        self._by_id: Dict[int, ItemEntry] = {}
        self._all: List[ItemEntry] = []
        self._name_to_id: Dict[str, int] = {}       # 원본 이름 exact 매칭
        self._norm_to_ids: Dict[str, List[int]] = {}  # 정규화 이름 -> id 후보들(동명이인 대비)

    def load(self) -> None:
        if self._loaded:
            return

        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"items.json not found: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        by_id: Dict[int, ItemEntry] = {}
        all_entries: List[ItemEntry] = []
        name_to_id: Dict[str, int] = {}
        norm_to_ids: Dict[str, List[int]] = {}

        for k, v in raw.items():
            try:
                item_id = int(k)
            except Exception:
                continue

            name = (v.get("name") or "").strip()
            icon = (v.get("icon") or "").strip()
            desc = (v.get("desc") or "").strip()
            category = (v.get("category") or "").strip()

            if not name:
                continue

            nn = _norm(name)
            ent = ItemEntry(
                item_id=item_id,
                name=name,
                icon=icon,
                desc=desc,
                category=category,
                name_norm=nn,
            )

            by_id[item_id] = ent
            all_entries.append(ent)

            # exact name → id (중복이면 첫 값 유지)
            name_to_id.setdefault(name, item_id)

            # norm → ids
            norm_to_ids.setdefault(nn, []).append(item_id)

        # 이름 기준 정렬(디버깅/결과 안정성)
        all_entries.sort(key=lambda e: e.name)

        self._by_id = by_id
        self._all = all_entries
        self._name_to_id = name_to_id
        self._norm_to_ids = norm_to_ids
        self._loaded = True

    def get(self, item_id: int) -> Optional[ItemEntry]:
        if not self._loaded:
            self.load()
        return self._by_id.get(int(item_id))

    def search(
        self,
        query: str,
        *,
        max_similar: int = 30,
        min_score: float = 0.55,
    ) -> Tuple[Optional[int], Optional[str], List[str]]:
        """
        기존 search_item() 시그니처에 맞춤:
        returns: (item_id, real_name, similar_names)
        """
        if not self._loaded:
            self.load()

        q = (query or "").strip()
        if not q:
            return None, None, []

        # 1) exact match 우선
        exact_id = self._name_to_id.get(q)
        if exact_id:
            ent = self._by_id.get(exact_id)
            return exact_id, ent.name if ent else q, self._similar_by_query(q, exclude_id=exact_id, max_similar=max_similar)

        qn = _norm(q)
        if not qn:
            return None, None, []

        # 2) norm exact match(공백/특수문자 차이)
        norm_ids = self._norm_to_ids.get(qn)
        if norm_ids:
            # 동명이인 있으면 첫 번째 사용, 나머지는 similar로 내림
            main_id = norm_ids[0]
            ent = self._by_id.get(main_id)
            similar = []
            for iid in norm_ids[1:]:
                e = self._by_id.get(iid)
                if e:
                    similar.append(e.name)
            # query 기반 유사 결과도 추가
            similar.extend(self._similar_by_query(q, exclude_id=main_id, max_similar=max_similar))
            # 중복 제거
            similar = _dedupe_keep(similar)[:max_similar]
            return main_id, ent.name if ent else q, similar

        # 3) substring 후보
        substr = [e for e in self._all if qn in e.name_norm]
        if substr:
            # 가장 짧은 이름(보통 더 정확) + 안정적인 tie-break
            substr.sort(key=lambda e: (len(e.name_norm), e.name))
            main = substr[0]
            similar = [e.name for e in substr[1: max_similar + 1]]
            return main.item_id, main.name, similar[:max_similar]

        # 4) fuzzy (difflib) - 느려질 수 있으니 점수 컷
        scored: List[Tuple[float, ItemEntry]] = []
        for e in self._all:
            # 간단 휴리스틱: 길이 차이 큰 건 대충 패스
            if abs(len(e.name_norm) - len(qn)) > 12:
                continue
            s = SequenceMatcher(None, qn, e.name_norm).ratio()
            if s >= min_score:
                scored.append((s, e))

        if not scored:
            return None, None, []

        scored.sort(key=lambda x: (-x[0], len(x[1].name_norm), x[1].name))
        main = scored[0][1]
        similar = [e.name for _, e in scored[1: max_similar + 1]]
        return main.item_id, main.name, similar[:max_similar]

    def _similar_by_query(self, query: str, *, exclude_id: int, max_similar: int) -> List[str]:
        qn = _norm(query)
        out: List[str] = []
        if not qn:
            return out
        # substring 유사
        for e in self._all:
            if e.item_id == exclude_id:
                continue
            if qn in e.name_norm or e.name_norm in qn:
                out.append(e.name)
                if len(out) >= max_similar:
                    break
        return out


def _dedupe_keep(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out