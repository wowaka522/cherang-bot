import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "cherang_love.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def init_love_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS love (
        user_id TEXT PRIMARY KEY,
        love INTEGER NOT NULL
    )
    """)
    conn.commit()
    conn.close()
    print(f"💘 LoveDB Init: {DB_PATH.resolve()}")

def get_user_love(user_id: str) -> int:
    init_love_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT love FROM love WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        print(f"🆕 New user {user_id} → love=0")
        return 0
    return row[0]

def change_user_love(user_id: str, delta: int):
    init_love_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT love FROM love WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    
    if row is None:
        new_love = max(0, delta)
        cur.execute(
            "INSERT INTO love (user_id, love) VALUES (?, ?)",
            (user_id, new_love)
        )
        print(f"💖 New user {user_id}: love={new_love}")
    else:
        new_love = max(0, row[0] + delta)
        cur.execute(
            "UPDATE love SET love=? WHERE user_id=?",
            (new_love, user_id)
        )
        print(f"✨ Update Love: {user_id}: {row[0]} → {new_love} (Δ{delta})")

    conn.commit()
    conn.close()
