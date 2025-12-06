# utils/db.py
import json
from pathlib import Path
from typing import Dict, Any

DB_PATH = Path("data") / "cherang_db.json"


def load_db() -> Dict[str, Any]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        save_db({})
        return {}

    try:
        return json.loads(DB_PATH.read_text("utf-8"))
    except Exception:
        save_db({})
        return {}


def save_db(data: Dict[str, Any]) -> None:
    DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=4), "utf-8")


def get_user(uid: int) -> Dict[str, Any]:
    db = load_db()
    key = str(uid)

    if key not in db:
        db[key] = {
            "love": 0,
            "money": 0,
            "inventory": {},
            "stats": {},
            "quests": {},
            "achievements": {}
        }
        save_db(db)

    return db[key]


def update_user(uid: int, info: Dict[str, Any]):
    db = load_db()
    db[str(uid)] = info
    save_db(db)
