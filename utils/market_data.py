# utils/market_data.py
from __future__ import annotations

import io
import time
import json
import urllib.request
import urllib.parse
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt


UNIVERSALIS_BASE = "https://universalis.app/api/v2"


def _http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_price(world_id: int, item_id: int) -> Optional[Dict[str, Any]]:
    """
    world_id / item_id 단일 조회.
    기존 market.py가 기대하는 형태(listings 포함)를 그대로 반환.
    """
    url = f"{UNIVERSALIS_BASE}/{world_id}/{item_id}"
    try:
        return _http_get_json(url)
    except Exception:
        return None


def format_price(n: int) -> str:
    # 1234567 -> 1,234,567
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def build_history_chart(server_name: str, world_id: int, item_id: int) -> Optional[io.BytesIO]:
    """
    market.py가 기대하는: BytesIO PNG 버퍼를 반환.
    Universalis history API를 간단히 사용해서 최근 7일 라인차트 생성.
    """
    # Universalis history endpoint:
    # /api/v2/history/{world}/{item}?entries=...
    # (정확한 파라미터는 조금 변동 가능하지만, 일단 이 형태로 동작하는 경우가 많음)
    url = f"{UNIVERSALIS_BASE}/history/{world_id}/{item_id}?entries=200"

    try:
        data = _http_get_json(url)
    except Exception:
        return None

    entries = data.get("entries") or []
    if not entries:
        return None

    # entries: [{"timestamp":..., "pricePerUnit":..., ...}, ...]
    # timestamp는 초 단위(epoch)인 경우가 많음
    xs = []
    ys = []
    now = time.time()
    week_ago = now - 7 * 24 * 3600

    for e in entries:
        ts = e.get("timestamp")
        p = e.get("pricePerUnit")
        if ts is None or p is None:
            continue
        # 초/밀리초 자동 보정
        ts = float(ts)
        if ts > 10_000_000_000:  # ms로 보이면
            ts = ts / 1000.0
        if ts < week_ago:
            continue
        xs.append(ts)
        ys.append(float(p))

    if len(xs) < 2:
        return None

    # 시간순 정렬
    pts = sorted(zip(xs, ys), key=lambda x: x[0])
    xs, ys = zip(*pts)

    plt.figure()
    plt.plot(xs, ys)
    plt.title(f"{server_name} - last 7d")
    plt.xlabel("time")
    plt.ylabel("price")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf