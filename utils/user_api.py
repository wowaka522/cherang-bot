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
