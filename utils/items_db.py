# utils/items_db.py

import json
import random
import os

# 데이터 경로
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

KR_ITEMS = {}
KR_DETAIL = {}

POTION_ITEMS = []
FOOD_ITEMS = []

GEAR_CATS = [
    "한손검","양손도끼","양손검","건블레이드","양손창","양손낫","격투무기","외날검",
    "쌍검","이도류무기","활","총","투척무기","한손 주술도구","양손 주술도구",
    "마도서","세검","붓","청마기","한손 환술도구","양손 환술도구",
    "학자용 마도서","천구의","현학도구","방패",
    "머리 방어구","몸통 방어구","손 방어구","다리 방어구","발 방어구",
    "귀걸이","목걸이","팔찌","반지"
]


def load_items():
    global KR_ITEMS, KR_DETAIL
    with open(os.path.join(DATA_DIR, "kr_items.json"), encoding="utf-8") as f:
        KR_ITEMS = json.load(f)
    with open(os.path.join(DATA_DIR, "kr_detail.json"), encoding="utf-8") as f:
        KR_DETAIL = json.load(f)


def get_item_category_by_id(item_id: str) -> str:
    info = KR_DETAIL.get(str(item_id))
    if not info:
        return ""
    return info.get("category", "")


def get_item_category_by_name(name: str) -> str:
    for iid, iname in KR_ITEMS.items():
        if iname == name:
            return get_item_category_by_id(iid)
    return ""


def is_gear_category(cat: str) -> bool:
    if cat in GEAR_CATS:
        return True
    return any(k in cat for k in ["방어구", "무기"])


def get_item_emoji(name: str) -> str:
    cat = get_item_category_by_name(name) or ""
    if cat == "요리":
        return "🍲"
    if cat == "약품":
        return "🧪"
    if is_gear_category(cat):
        return "⚔️"
    return "📦"


def build_category_lists():
    global POTION_ITEMS, FOOD_ITEMS
    POTION_ITEMS = []
    FOOD_ITEMS = []

    for iid, name in KR_ITEMS.items():
        cat = get_item_category_by_id(iid)
        if cat == "약품":
            POTION_ITEMS.append(name)
        elif cat == "요리":
            FOOD_ITEMS.append(name)

    print(f"✔ 약품={len(POTION_ITEMS)}, 요리={len(FOOD_ITEMS)}")


def random_gear_name() -> str | None:
    candidates = []
    for iid, name in KR_ITEMS.items():
        cat = get_item_category_by_id(iid)
        if is_gear_category(cat):
            candidates.append(name)
    if not candidates:
        return None
    return random.choice(candidates)

def get_item_id_by_name(item_name: str) -> str | None:
    """아이템 이름으로 item_id 찾기"""
    for iid, name in KR_ITEMS.items():
        if name == item_name:
            return iid
    return None

def get_item_name_by_id(item_id: str) -> str:
    return KR_ITEMS.get(str(item_id), "???")



# 최초 호출
load_items()
build_category_lists()
