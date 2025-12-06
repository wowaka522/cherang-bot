import json
from pathlib import Path

DB_PATH = Path("data") / "love_db.json"


def load_db():
    if not DB_PATH.exists():
        save_db({})
        return {}
    try:
        return json.loads(DB_PATH.read_text("utf-8"))
    except:
        save_db({})
        return {}


def save_db(db: dict):
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=4), "utf-8")


def get_user_love(user_id: str) -> int:
    db = load_db()
    return db.get(user_id, 0)


def change_user_love(user_id: str, amount: int) -> int:
    db = load_db()
    new_value = db.get(user_id, 0) + amount
    db[user_id] = new_value
    save_db(db)
    return new_value
