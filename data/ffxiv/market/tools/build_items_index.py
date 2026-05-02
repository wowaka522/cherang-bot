import csv
import json
import sys
from pathlib import Path

# 콘솔 한글 깨짐 방지
try:
    sys.stdout.reconfigure(encoding="utf-8")
except:
    pass


def _parse_int(v, default=0):
    try:
        return int(str(v or "").strip())
    except:
        return default


def _build_icon_path(icon_value):
    icon_id = _parse_int(icon_value)
    if icon_id <= 0:
        return ""

    folder = (icon_id // 1000) * 1000
    return f"{folder:06d}/{icon_id:06d}.png"


def find_repo_root(start: Path):
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / "data").exists():
            return p
    return start.resolve().parents[0]


# 🔥 SaintCoinach CSV 파서 (핵심)
def read_sc_csv_dicts(csv_path: Path):
    if not csv_path.exists():
        print(f"❌ 파일 없음: {csv_path}")
        return

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

        if len(rows) < 4:
            return

        headers = rows[1]   # 실제 컬럼명
        data_rows = rows[3:]  # 실제 데이터

        for row in data_rows:
            if not row:
                continue
            yield dict(zip(headers, row))


def build_items_index(item_csv_path: Path):
    final_data = {}
    stats = {"scanned": 0, "valid": 0}

    for row in read_sc_csv_dicts(item_csv_path):
        stats["scanned"] += 1

        item_id = _parse_int(row.get("#") or row.get("Key"))
        if item_id <= 0:
            continue

        name = str(row.get("Name", "")).strip()
        if not name:
            continue

        # 🔥 거래불가 필터 (가장 안정적인 방식)
        if str(row.get("IsUntradable")).strip().upper() == "TRUE":
            continue

        icon_path = _build_icon_path(row.get("Icon"))

        final_data[str(item_id)] = {
            "name": name,
            "icon": icon_path,
            "cat": str(row.get("ItemUICategory") or "").strip(),
        }

        stats["valid"] += 1

    return final_data, stats


def main():
    root = find_repo_root(Path(__file__))

    item_csv_path = root / "data" / "ffxiv" / "fish" / "raw" / "csv" / "ko" / "Item.csv"
    out_json_path = root / "data" / "ffxiv" / "market" / "compiled" / "items.json"

    print("📂 Loading...")
    data, stats = build_items_index(item_csv_path)

    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("✅ 완료")
    print(f"scanned: {stats['scanned']:,}")
    print(f"valid: {stats['valid']:,}")


if __name__ == "__main__":
    main()