# utils/items.py
import re
from pathlib import Path
from typing import Dict, List, Tuple

RAPHAEL_ROOT = Path("raphael") / "raphael-rs"
ITEM_NAMES_RS = RAPHAEL_ROOT / "raphael-data" / "data" / "item_names_kr.rs"
MEALS_RS = RAPHAEL_ROOT / "raphael-data" / "data" / "meals.rs"
POTIONS_RS = RAPHAEL_ROOT / "raphael-data" / "data" / "potions.rs"

MEAL_ITEMS: Dict[int, str] = {}
POTION_ITEMS: Dict[int, str] = {}


def _load_ids_from(path: Path, label: str) -> set[int]:
    if not path.exists():
        print(f"⚠ {label} 파일 없음: {path}")
        return set()
    text = path.read_text("utf-8", "ignore")
    ids = {int(i) for i in re.findall(r"item_id:\s*(\d+)", text)}
    print(f"✨ {label} item_id {len(ids)}개 로드")
    return ids


def load_meals_and_potions() -> None:
    global MEAL_ITEMS, POTION_ITEMS

    if not ITEM_NAMES_RS.exists():
        print(f"⚠ item_names_kr.rs 없음: {ITEM_NAMES_RS}")
        MEAL_ITEMS, POTION_ITEMS = {}, {}
        return

    names_text = ITEM_NAMES_RS.read_text("utf-8", "ignore")
    names: Dict[int, str] = {}
    for mid, name in re.findall(r"(\d+)\s*=>\s*\"([^\"]+)\"", names_text):
        names[int(mid)] = name

    meal_ids = _load_ids_from(MEALS_RS, "meals")
    potion_ids = _load_ids_from(POTIONS_RS, "potions")

    MEAL_ITEMS = {iid: names.get(iid, f"#{iid}") for iid in meal_ids}
    POTION_ITEMS = {iid: names.get(iid, f"#{iid}") for iid in potion_ids}

    print(f"🍽 음식 {len(MEAL_ITEMS)}개, 🧪 약 {len(POTION_ITEMS)}개 매핑 완료")


def search_meal_items(keyword: str) -> List[Tuple[int, str]]:
    kw = keyword.strip().lower()
    if not kw:
        return []
    res = [(iid, name) for iid, name in MEAL_ITEMS.items() if kw in name.lower()]
    res.sort(key=lambda x: x[1])
    return res[:25]


def search_potion_items(keyword: str) -> List[Tuple[int, str]]:
    kw = keyword.strip().lower()
    if not kw:
        return []
    res = [(iid, name) for iid, name in POTION_ITEMS.items() if kw in name.lower()]
    res.sort(key=lambda x: x[1])
    return res[:25]