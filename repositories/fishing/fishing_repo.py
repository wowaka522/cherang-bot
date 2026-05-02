# repositories/fishing/fishing_repo.py
from __future__ import annotations
from typing import Any, Dict, List, Set
from repositories.base_repo import BaseRepo

class FishingRepo(BaseRepo):
    def __init__(self, data_dir="data") -> None:
        super().__init__(data_dir=data_dir)

    def load_spots(self) -> Any:
        return self._load_json("fishing_spots.json")

    def load_big_fish(self) -> Any:
        return self._load_json("Big_Fish.json")

    def get_big_fish_set(self) -> Set[str]:
        data = self.load_big_fish()
        # TODO: Big_Fish.json 구조에 맞춰 파싱
        # 일단 리스트라고 가정
        if isinstance(data, list):
            return set(data)
        return set()
