import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd


# =========================
# Helpers
# =========================
def safe_get_str(row: Any, key: str, default: str = "") -> str:
    try:
        v = row.get(key, default) if hasattr(row, "get") else row[key]
    except Exception:
        return default
    if v is None:
        return default
    if isinstance(v, float) and pd.isna(v):
        return default
    s = str(v).strip()
    if s.lower() == "nan":
        return default
    return s


def norm_id(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return ""
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    return s


def transform_icon_to_fish_tex(icon_tex: str) -> str:
    """
    아이콘 경로 안 숫자를 +50000 해서 fish(어탁/큰 아이콘) tex 경로로 변환.
    예: ui/icon/029000/029055.tex -> ui/icon/079000/079055.tex 같은 형태로.
    """
    if not isinstance(icon_tex, str) or not icon_tex or icon_tex == "nan":
        return ""
    return re.sub(r"(\d+)", lambda m: f"{int(m.group(0)) + 50000:06d}", icon_tex)


def read_ffxiv_csv(path: str) -> pd.DataFrame:
    """
    FFXIV csv는 보통 3줄짜리 헤더가 껴있음.
    (네 파일들 기준으로 아래 방식이 잘 먹음)
    """
    try:
        df = pd.read_csv(path, header=[1], low_memory=False, skiprows=[2])
        if df.shape[1] > 1:
            return df
    except Exception:
        pass

    try:
        df = pd.read_csv(path, header=[0, 1, 2], low_memory=False)
        return df
    except Exception:
        pass

    return pd.read_csv(path, header=None, low_memory=False, skiprows=3)


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if any(isinstance(c, tuple) for c in df.columns):
        df.columns = [
            c[1] if (isinstance(c, tuple) and len(c) > 1) else str(c)
            for c in df.columns
        ]
    return df


# =========================
# data.js parsing (FISH object)
# =========================
FISH_OBJ_RE = re.compile(r"\bFISH\s*:\s*\{", re.DOTALL)


def extract_fish_object_text(data_js_text: str) -> str:
    m = FISH_OBJ_RE.search(data_js_text)
    if not m:
        return ""
    i = m.end()
    depth = 1
    start = i
    j = i
    while j < len(data_js_text):
        ch = data_js_text[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return data_js_text[start:j]
        j += 1
    return ""


def iter_fish_blocks(fish_obj_text: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    key_re = re.compile(r'"(\d+)"\s*:\s*\{', re.DOTALL)
    pos = 0
    while True:
        m = key_re.search(fish_obj_text, pos)
        if not m:
            break
        fid = m.group(1)
        brace_start = m.end()
        depth = 1
        j = brace_start
        while j < len(fish_obj_text):
            ch = fish_obj_text[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    block = fish_obj_text[brace_start:j]
                    out.append((fid, block))
                    pos = j + 1
                    break
            j += 1
        else:
            break
    return out


def parse_simple_val(block_txt: str, key: str) -> Optional[str]:
    m = re.search(fr'"{re.escape(key)}"\s*:\s*([^,\]}}]+)', block_txt)
    if not m:
        return None
    raw = m.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return raw


def parse_array_vals(block_txt: str, key: str) -> List[str]:
    m = re.search(fr'"{re.escape(key)}"\s*:\s*\[([^\]]*)\]', block_txt)
    if not m:
        return []
    inside = m.group(1).strip()
    if not inside:
        return []
    parts = [p.strip() for p in inside.split(",")]
    out: List[str] = []
    for p in parts:
        if not p or p.lower() == "null":
            continue
        if p.startswith('"') and p.endswith('"'):
            p = p[1:-1]
        out.append(norm_id(p))
    return [x for x in out if x]


def parse_predators(block_txt: str) -> Dict[str, Any]:
    m = re.search(r'"predators"\s*:\s*(\[[\s\S]*?\]|\{[\s\S]*?\}|null)', block_txt)
    if not m:
        return {}
    raw = m.group(1).strip()
    if raw == "null":
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw}


def build_datajs_fish_map(data_js_text: str) -> Dict[str, Dict[str, Any]]:
    fish_obj = extract_fish_object_text(data_js_text)
    blocks = iter_fish_blocks(fish_obj)

    out: Dict[str, Dict[str, Any]] = {}
    for fid, block in blocks:
        big_fish = (parse_simple_val(block, "bigFish") or "").lower() == "true"
        out[fid] = {
            "is_teoju": big_fish,
            "start": parse_simple_val(block, "startHour"),
            "end": parse_simple_val(block, "endHour"),
            "tug": parse_simple_val(block, "tug"),
            "hookset": parse_simple_val(block, "hookset"),
            "patch": parse_simple_val(block, "patch"),
            "location_id": parse_simple_val(block, "location"),
            "bestCatchPath": parse_array_vals(block, "bestCatchPath"),
            "previousWeatherSet": parse_array_vals(block, "previousWeatherSet"),
            "weatherSet": parse_array_vals(block, "weatherSet"),
            "predators": parse_predators(block),
            "intuitionLength": parse_simple_val(block, "intuitionLength"),
        }
    return out


# =========================
# Maps from CSV
# =========================
def build_item_ko_maps(item_ko_path: str) -> Tuple[Dict[str, Dict[str, str]], Dict[str, str]]:
    """
    Item_ko.csv(헤더3줄) 기준:
      col0: id
      col10: ko name
      col11: icon tex
      col16: category(문자열)
    """
    df = pd.read_csv(item_ko_path, header=None, low_memory=False, skiprows=3)
    id_to_ko: Dict[str, Dict[str, str]] = {}
    name_to_id: Dict[str, str] = {}

    for _, row in df.iterrows():
        iid = norm_id(row[0])
        if not iid:
            continue
        name_ko = str(row[10]).strip() if len(row) > 10 else ""
        icon = str(row[11]).strip() if len(row) > 11 else ""
        cat = str(row[16]).strip() if len(row) > 16 else ""
        id_to_ko[iid] = {"name": name_ko, "icon": icon, "cat": cat}
        if name_ko:
            name_to_id[name_ko] = iid

    return id_to_ko, name_to_id


def build_fish_desc_map(fishparam_path: str) -> Dict[str, str]:
    fp = flatten_columns(read_ffxiv_csv(fishparam_path))
    out: Dict[str, str] = {}
    if "Item" in fp.columns and "Text" in fp.columns:
        for _, r in fp.iterrows():
            nm = safe_get_str(r, "Item", "")
            txt = safe_get_str(r, "Text", "")
            if nm:
                out[nm] = txt.replace("\r\n", "\n")
    return out


def parse_intended_use(v: str) -> Optional[int]:
    """
    TerritoryType.TerritoryIntendedUse가 'TerritoryIntendedUse#1' 같은 형태.
    """
    if not v:
        return None
    m = re.search(r"#(\d+)", v)
    if not m:
        return None
    return int(m.group(1))


def build_territory_map(tt_path: str) -> Dict[str, Dict[str, Any]]:
    """
    key: TerritoryType.Name (ex f1f1)
    fields:
      - continent/region/sub_region/zone/territory
      - intended_use (int)
    """
    tt = flatten_columns(read_ffxiv_csv(tt_path))

    out: Dict[str, Dict[str, Any]] = {}
    for _, r in tt.iterrows():
        code = safe_get_str(r, "Name", "")
        if not code:
            continue

        # 네 데이터 기준
        region = safe_get_str(r, "PlaceName{Region}", "")
        zone = safe_get_str(r, "PlaceName{Zone}", "")
        territory = safe_get_str(r, "PlaceName", "")
        intended_raw = safe_get_str(r, "TerritoryIntendedUse", "")
        intended = parse_intended_use(intended_raw)

        # continent는 딱히 따로 없어서 region을 재사용(네 출력도 이 형태였음)
        out[code] = {
            "continent": region,
            "region": region,
            "sub_region": territory,   # '검은장막 숲 중부삼림' 같은 세부
            "zone": zone or region,
            "territory": territory,
            "intended_use": intended,
        }

    return out


# =========================
# Build SPOTS (filtering special spots)
# =========================
DEFAULT_ALLOWED_INTENDED_USE = {0, 1, 13}  # 도시/필드/거주구(바깥)


def build_spot_db(
    fs_path: str,
    territory_map: Dict[str, Dict[str, Any]],
    allowed_intended_use: Set[int] = DEFAULT_ALLOWED_INTENDED_USE,
) -> Dict[str, Dict[str, Any]]:
    fs = flatten_columns(read_ffxiv_csv(fs_path))
    spot_db: Dict[str, Dict[str, Any]] = {}

    for _, r in fs.iterrows():
        sid = norm_id(safe_get_str(r, "#", ""))
        if not sid:
            continue

        spot_name = safe_get_str(r, "PlaceName", "")
        if not spot_name or spot_name in ["0", "미지의 낚시터"]:
            continue

        tcode = safe_get_str(r, "TerritoryType", "")
        tinfo = territory_map.get(tcode, {})
        intended = tinfo.get("intended_use", None)

        # 1) intended use allowlist 필터 (특수/임무/인던 계열 제거용)
        if intended is None or intended not in allowed_intended_use:
            continue

        continent = tinfo.get("continent", "")
        region = tinfo.get("region", "")
        sub_region = tinfo.get("sub_region", "")
        zone = tinfo.get("zone", "")
        territory = tinfo.get("territory", "")

        # 2) 계층이 비면 "낚시터만 덜렁" 케이스일 확률 높음 -> 제거
        if not continent or not region or not sub_region:
            continue

        fish_list: List[str] = []
        for i in range(10):
            v = safe_get_str(r, f"Item[{i}]", "")
            if v and v != "0":
                fish_list.append(v)

        # fish_list가 비면 의미 없음
        if not fish_list:
            continue

        spot_db[sid] = {
            "name": spot_name,
            "continent": continent,
            "region": region,
            "sub_region": sub_region,
            "zone": zone,
            "territory": territory,
            "on_reach": safe_get_str(r, "BigFish{OnReach}", ""),
            "on_end": safe_get_str(r, "BigFish{OnEnd}", ""),
            "fish_list": fish_list,
            # teuju_list는 FISH 만든 뒤에 채움
            "teoju_list": [],
        }

    return spot_db


def build_spots_tree(spot_db: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    tree: Dict[str, Any] = {}
    for sid, info in spot_db.items():
        c = info.get("continent") or "기타"
        r = info.get("region") or "기타"
        sr = info.get("sub_region") or "기타"
        tree.setdefault(c, {}).setdefault(r, {}).setdefault(sr, {})[sid] = info.get("name", "")
    return tree


# =========================
# Build FISH (ALL fish in surviving spots)
# =========================
def build_fish_all(
    valid_fish_names: Set[str],
    id_to_ko: Dict[str, Dict[str, str]],
    ko_name_to_id: Dict[str, str],
    desc_map: Dict[str, str],
    datajs_fish_map: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], Set[str]]:
    """
    FISH는 '터주만'이 아니라 valid_fish_names(= 살아남은 스팟 fish_list 전체)로 만든다.
    - 기본정보: Item_ko + FishParameter
    - 조건정보: data.js에 해당 id가 있으면 덮어쓰기
    - 터주여부: data.js bigFish(true)로 is_teoju 플래그
    """
    fish_db: Dict[str, Dict[str, Any]] = {}
    teuju_id_set: Set[str] = set()

    # valid fish name -> id
    for name in sorted(valid_fish_names):
        fid = ko_name_to_id.get(name, "")
        if not fid:
            # 한글 매칭이 안 되면 일단 스킵(원하면 여기 로그 찍어도 됨)
            continue

        info = id_to_ko.get(fid, {"name": name, "icon": "", "cat": ""})
        icon_tex = info.get("icon", "") or ""
        fish_tex = transform_icon_to_fish_tex(icon_tex)

        base = {
            "name_ko": info.get("name", name) or name,
            "desc": desc_map.get(name, ""),
            "category": info.get("cat", ""),
            "icon_tex": icon_tex,
            "fish_tex": fish_tex,

            # 기본값(조건 없는 일반 물고기 대비)
            "is_teoju": False,
            "start": None,
            "end": None,
            "tug": None,
            "hookset": None,
            "bait_path": [],

            # 조건 데이터(있으면 채움)
            "previousWeatherSet": [],
            "weatherSet": [],
            "predators": {},
            "intuitionLength": None,
            "patch": None,
            "location_id": None,
        }

        # data.js 덮어쓰기(조건부/터주)
        dj = datajs_fish_map.get(fid)
        if dj:
            base["is_teoju"] = bool(dj.get("is_teoju", False))
            if base["is_teoju"]:
                teuju_id_set.add(fid)

            # 시간/입질/훅셋
            base["start"] = dj.get("start")
            base["end"] = dj.get("end")
            base["tug"] = dj.get("tug")
            base["hookset"] = dj.get("hookset")
            base["patch"] = dj.get("patch")
            base["location_id"] = dj.get("location_id")

            # 날씨/직감
            base["previousWeatherSet"] = dj.get("previousWeatherSet") or []
            base["weatherSet"] = dj.get("weatherSet") or []
            base["predators"] = dj.get("predators") or {}
            base["intuitionLength"] = dj.get("intuitionLength")

            # 미끼 경로(bestCatchPath id -> 이름)
            bait_ids = dj.get("bestCatchPath") or []
            bait_names: List[str] = []
            for bid in bait_ids:
                b = id_to_ko.get(bid)
                if b and b.get("name"):
                    bait_names.append(b["name"])
            base["bait_path"] = bait_names

        fish_db[fid] = base

    return fish_db, teuju_id_set


def fill_spot_teoju_list(
    spot_db: Dict[str, Dict[str, Any]],
    ko_name_to_id: Dict[str, str],
    teuju_id_set: Set[str],
):
    for sid, info in spot_db.items():
        lst = []
        for nm in info.get("fish_list", []):
            fid = ko_name_to_id.get(nm, "")
            if fid and fid in teuju_id_set:
                lst.append(nm)
        info["teoju_list"] = lst


# =========================
# Main build
# =========================
def build_final_db(
    data_js_path: str,
    fishing_spot_path: str,
    territory_type_path: str,
    item_ko_path: str,
    fishparam_path: str,
    out_path: str,
):
    with open(data_js_path, "r", encoding="utf-8") as f:
        data_js_text = f.read()

    territory_map = build_territory_map(territory_type_path)
    spot_db = build_spot_db(fishing_spot_path, territory_map)

    # ✅ 살아남은 스팟에 등장하는 물고기만 "유효 어종"으로 채택
    valid_names: Set[str] = set()
    for s in spot_db.values():
        valid_names.update(s.get("fish_list", []))

    id_to_ko, ko_name_to_id = build_item_ko_maps(item_ko_path)
    desc_map = build_fish_desc_map(fishparam_path)
    datajs_fish_map = build_datajs_fish_map(data_js_text)

    fish_db, teuju_ids = build_fish_all(
        valid_fish_names=valid_names,
        id_to_ko=id_to_ko,
        ko_name_to_id=ko_name_to_id,
        desc_map=desc_map,
        datajs_fish_map=datajs_fish_map,
    )

    fill_spot_teoju_list(spot_db, ko_name_to_id, teuju_ids)

    result = {
        "FISH": fish_db,          # ✅ 모든 어종(=유효 스팟에 나오는 것 전부)
        "SPOTS": spot_db,         # ✅ 필드 기반 스팟만 남김
        "SPOTS_TREE": build_spots_tree(spot_db),
        "_meta": {
            "fish_count": len(fish_db),
            "spot_count": len(spot_db),
            "teoju_count": len(teuju_ids),
            "allowed_intended_use": sorted(list(DEFAULT_ALLOWED_INTENDED_USE)),
        },
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ build ok")
    print(f" - FISH: {len(fish_db)} (valid spot fish only)")
    print(f" - SPOTS: {len(spot_db)} (filtered)")
    print(f" - 터주(teoju): {len(teuju_ids)}")


if __name__ == "__main__":
    # 이 스크립트 파일 위치 기준으로 fish 폴더 잡기
    base = Path(__file__).resolve().parent.parent  # .../data/ffxiv/fish
    raw = base / "raw"
    compiled = base / "compiled"

    # ✅ 너 올인원 구조: SaintCoinach KO는 여기로 떨어짐
    csv_ko = raw / "csv" / "ko"
    csv_root = raw / "csv"

    def pick_csv(name: str) -> Path:
        """ko 폴더 우선, 없으면 기존 위치 fallback"""
        p = csv_ko / name
        if p.exists():
            return p
        return csv_root / name

    build_final_db(
        data_js_path=str(raw / "data.js"),
        fishing_spot_path=str(pick_csv("FishingSpot.csv")),
        territory_type_path=str(pick_csv("TerritoryType.csv")),
        # ✅ 너는 Item_ko.csv가 아니라 Item.csv가 생성됨(SC export Item)
        item_ko_path=str(pick_csv("Item.csv")),
        fishparam_path=str(pick_csv("FishParameter.csv")),
        out_path=str(compiled / "final_fishing_db.json"),
    )