# utils/state.py
import json
from pathlib import Path

MONEY_FILE = Path("data/money_data.json")
INV_FILE = Path("data/inven_data.json")
LOVE_FILE = Path("data/love_data.json")

money_db = {}
inventories = {}
love_db = {}


# ===== JSON Load/Save =====
def load_json(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        save_json(path, default)
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        save_json(path, default)
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def load_all():
    global money_db, inventories, love_db
    money_db = load_json(MONEY_FILE, {})
    inventories = load_json(INV_FILE, {})
    love_db = load_json(LOVE_FILE, {})


def save_money():
    save_json(MONEY_FILE, money_db)


def save_inven():
    save_json(INV_FILE, inventories)


def save_love():
    save_json(LOVE_FILE, love_db)


# ===== 경제 =====
def get_money(uid: str) -> int:
    return money_db.get(uid, 0)


def add_money(uid: str, amount: int):
    money_db[uid] = get_money(uid) + amount
    save_money()


def spend_money(uid: str, amount: int) -> bool:
    if get_money(uid) < amount:
        return False
    money_db[uid] -= amount
    save_money()
    return True


# ===== 인벤토리 =====
def get_inventory(uid: str):
    return inventories.get(uid, {})


def add_item(uid: str, name: str, count: int = 1):
    inv = inventories.setdefault(uid, {})
    inv[name] = inv.get(name, 0) + count
    save_inven()


def remove_item(uid: str, name: str, count: int = 1) -> bool:
    inv = inventories.setdefault(uid, {})
    if inv.get(name, 0) < count:
        return False
    inv[name] -= count
    if inv[name] <= 0:
        del inv[name]
    save_inven()
    return True


# ===== 호감도 =====
def get_user_love(user) -> int:
    uid = str(user.id)
    love_db.setdefault(uid, {"score": 0})
    return love_db[uid]["score"]


def change_user_love(user, delta: int) -> int:
    uid = str(user.id)
    love_db.setdefault(uid, {"score": 0})
    love_db[uid]["score"] = max(-100, min(100, love_db[uid]["score"] + delta))
    save_love()
    return love_db[uid]["score"]
