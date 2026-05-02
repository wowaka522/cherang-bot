# services/fishing/fishing_core.py
# (Discord 의존 X) 낚시 판정/확률 뼈대
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Sequence, Set, Literal

HookResult = Literal["too_early", "success", "too_late", "bait_stolen"]

@dataclass
class BiteWindow:
    # 훅 적정 시간(초) 범위
    start: float
    end: float

def roll_bite_delay(min_s: float = 2.0, max_s: float = 6.0) -> float:
    return random.uniform(min_s, max_s)

def roll_window(width_s: float = 1.2) -> BiteWindow:
    # 예: 찌가 움직인 시점부터 width_s 동안이 적정
    return BiteWindow(start=0.0, end=width_s)

def judge_hook(elapsed_from_bite: float, window: BiteWindow, bait_stolen_chance: float = 0.08) -> HookResult:
    # elapsed_from_bite: 찌 움직인 이후 경과 시간
    if elapsed_from_bite < window.start:
        # 너무 빠름
        return "too_early"
    if window.start <= elapsed_from_bite <= window.end:
        # 적정
        return "success"
    # 너무 늦음(여기서 낮은 확률로 "미끼만 먹고 튐" 연출)
    if random.random() < bait_stolen_chance:
        return "bait_stolen"
    return "too_late"

def roll_fish(spot_fish: Sequence[str], big_fish_set: Set[str], normal_ratio_range=(0.80, 0.90)) -> str:
    # big_fish에 없는 애들 80~90% 확률로 나오게(나머지에 big)
    if not spot_fish:
        return "UNKNOWN"
    normal = [f for f in spot_fish if f not in big_fish_set]
    big = [f for f in spot_fish if f in big_fish_set]
    normal_ratio = random.uniform(*normal_ratio_range)

    if big and random.random() > normal_ratio:
        return random.choice(big)
    # normal 없으면 big로 폴백
    if normal:
        return random.choice(normal)
    return random.choice(big) if big else random.choice(list(spot_fish))
