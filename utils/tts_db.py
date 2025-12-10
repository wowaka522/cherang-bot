import json
from pathlib import Path

DB_PATH = Path("data") / "tts_voices.json"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_db():
    if not DB_PATH.exists():
        return {}
    with DB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with DB_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def set_voice(user_id: int, voice: str):
    db = load_db()
    db[str(user_id)] = voice
    save_db(db)

def get_voice(user_id: int):
    db = load_db()
    return db.get(str(user_id), "female_a")  # 기본값 여성 A

