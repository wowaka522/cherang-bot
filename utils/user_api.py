from .db import get_user, update_user

def add_money(uid: int, amount: int):
    data = get_user(uid)
    data["money"] += amount
    update_user(uid, data)
    return data["money"]

def add_love(uid: int, amount: int):
    data = get_user(uid)
    data["love"] += amount
    update_user(uid, data)
    return data["love"]

def add_item(uid: int, name: str, amount: int = 1):
    data = get_user(uid)
    inv = data["inventory"]
    inv[name] = inv.get(name, 0) + amount
    update_user(uid, data)
    return inv[name]

def remove_item(user_id: int, item_name: str, amount: int = 1) -> bool:
    """인벤에서 아이템 제거 (성공: True / 실패: False)"""
    data = get_user(user_id)
    inv = data.get("inventory", {})

    if inv.get(item_name, 0) < amount:
        return False

    inv[item_name] -= amount
    if inv[item_name] <= 0:
        del inv[item_name]

    data["inventory"] = inv
    update_user(user_id, data)
    return True

# ==========================
# 호감도 관련
# ==========================

def get_user_love(user_id: int) -> int:
    data = get_user(user_id)
    return data.get("love", 0)


def add_love(user_id: int, amount: int):
    data = get_user(user_id)
    current = data.get("love", 0)
    data["love"] = max(-100, min(100, current + amount))  # -100 ~ 100 제한
    update_user(user_id, data)

