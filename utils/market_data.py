import os
import json
import requests
import io
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# matplotlib + 폰트 설정
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 폰트 2개 모두 로드 (Regular + Bold)
font_regular = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_bold = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

fm.fontManager.addfont(font_regular)
fm.fontManager.addfont(font_bold)

# 실제 family name을 강제로 override
matplotlib.rcParams['font.family'] = 'Noto Sans CJK KR'
matplotlib.rcParams['axes.unicode_minus'] = False


# ===== 데이터 파일 경로 =====
DATA_DIR = os.path.join("data")

ITEMS_PATH  = os.path.join(DATA_DIR, "kr_items.json")
ICONS_PATH  = os.path.join(DATA_DIR, "kr_icons.json")
DETAIL_PATH = os.path.join(DATA_DIR, "kr_detail.json")

KR_ITEMS = {}
KR_ICONS = {}
KR_DETAIL = {}

def load_market_db():
    global KR_ITEMS, KR_ICONS, KR_DETAIL

    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            KR_ITEMS = json.load(f)
        print(f"✨ KR_ITEMS: {len(KR_ITEMS)}개 로드 완료")
    except:
        print("⚠ KR_ITEMS 로드 실패")

    try:
        with open(ICONS_PATH, "r", encoding="utf-8") as f:
            KR_ICONS = json.load(f)
        print(f"🖼 KR_ICONS: {len(KR_ICONS)}개 로드 완료")
    except:
        print("⚠ KR_ICONS 로드 실패")

    try:
        with open(DETAIL_PATH, "r", encoding="utf-8") as f:
            KR_DETAIL = json.load(f)
        print(f"📘 KR_DETAIL: {len(KR_DETAIL)}개 로드 완료")
    except:
        print("⚠ KR_DETAIL 로드 실패")


load_market_db()


# ===== 아이템 검색 =====
def search_item(query: str):
    query = query.strip()
    if not query:
        return None, None, []

    exact = [(iid, name) for iid, name in KR_ITEMS.items() if name == query]
    if exact:
        iid, name = exact[0]
        similar = [n for _, n in exact[1:6]]
        return int(iid), name, similar

    parts = query.split()
    results = []
    for iid, name in KR_ITEMS.items():
        score = 0
        lower_name = name.lower()
        for p in parts:
            if p.lower() in lower_name:
                score += 1
        if score > 0:
            results.append((score, int(iid), name))

    if not results:
        return None, None, []

    results.sort(reverse=True, key=lambda x: x[0])
    _, best_id, best_name = results[0]
    similar = [n for _, _, n in results[1:6]]
    return best_id, best_name, similar


def format_price(num):
    return f"{int(num):,} 길"


# ===== 시세 API =====
PRICE_URL = "https://universalis.app/api/v2/{world}/{item}"
HISTORY_URL = "https://universalis.app/api/v2/history/{world}/{item}"

def get_price(world_id: int, item_id: int):
    try:
        r = requests.get(PRICE_URL.format(world=world_id, item=item_id), timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None

def get_history(world_id: int, item_id: int):
    try:
        r = requests.get(HISTORY_URL.format(world=world_id, item=item_id), timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None


# ===== 그래프 생성 =====
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def build_history_chart(world_name: str, world_id: int, item_id: int):
    data = get_history(world_id, item_id)
    if not data or not data.get("entries"):
        return None

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    hq_by_day = defaultdict(list)
    nq_by_day = defaultdict(list)

    for e in data["entries"]:
        price = e.get("pricePerUnit")
        ts = e.get("timestamp")
        if not price or not ts:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt < start:
            continue
        d = dt.date()
        (hq_by_day if e.get("hq") else nq_by_day)[d].append(price)

    days = [(now.date() - timedelta(days=i)) for i in range(6, -1, -1)]
    x = list(range(len(days)))
    labels = [d.strftime("%m-%d") for d in days]

    hq_prices = [(sum(hq_by_day[d])/len(hq_by_day[d]) if d in hq_by_day else None) for d in days]
    nq_prices = [(sum(nq_by_day[d])/len(nq_by_day[d]) if d in nq_by_day else None) for d in days]

    if all(v is None for v in hq_prices + nq_prices):
        return None

    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    fig.patch.set_facecolor("#101322")
    ax.set_facecolor("#14182b")

    if any(nq_prices):
        ax.plot(x, [v if v is not None else float("nan") for v in nq_prices], marker="o", linewidth=2, label="NQ")
    if any(hq_prices):
        ax.plot(x, [v if v is not None else float("nan") for v in hq_prices], marker="o", linewidth=2, label="HQ")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8, color="#ddd")
    ax.tick_params(colors="#ddd")
    ax.set_title(f"{world_name} 최근 7일 평균 가격", fontsize=10, color="#ffcc66")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf