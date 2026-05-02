import csv
import io
import os
import json
import re

# -----------------------------------------------------------------------------
# 설정: 경로 자동 설정
# -----------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# 폴더 구조가 없는 경우 현재 폴더(.)를 사용하도록 수정
RAW_EN_DIR = os.path.join(BASE_DIR, "raw", "en")
RAW_KO_DIR = os.path.join(BASE_DIR, "raw", "ko")

OUTPUT_DIR = os.path.join(BASE_DIR, "compiled")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Robust helpers
# -----------------------------------------------------------------------------
_NUM_RE = re.compile(r"(-?\d+)")

def to_int_ref(v, default=0):
    """
    값이 '123' 이거나 'PlaceName#123' 같은 형태여도 숫자만 뽑아서 int로 변환.
    실패하면 default.
    """
    if v is None:
        return default
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if not s:
        return default
    
    # 순수 텍스트(예: "행성 파엔나")인 경우 숫자가 없으므로 default 반환
    m = _NUM_RE.search(s)
    if not m:
        return default
    try:
        return int(m.group(1))
    except Exception:
        return default

def read_ffxiv_table(base_path, fallback_path=None):
    """
    파일 읽기 로직: 지정된 경로에 없으면 fallback 경로(현재 폴더 등) 확인
    """
    target_path = base_path
    if not os.path.exists(target_path):
        if fallback_path and os.path.exists(fallback_path):
            target_path = fallback_path
        else:
            # 파일이 없으면 빈 리스트 반환하되 경고 출력은 생략 가능
            return []

    try:
        text = open(target_path, "r", encoding="utf-8-sig", errors="replace").read()
    except Exception as e:
        print(f"[오류] 파일 읽기 실패: {target_path} / {e}")
        return []

    # delimiter 감지
    raw_lines = text.splitlines()
    header_line = None
    for ln in raw_lines[:50]:
        if ln.startswith("#"):
            header_line = ln
            break
    if header_line is None:
        header_line = raw_lines[0] if raw_lines else ""

    delim = "\t" if header_line.count("\t") >= header_line.count(",") else ","

    f = io.StringIO(text)
    reader = csv.reader(f, delimiter=delim)
    rows = [r for r in reader if r and any(c.strip() for c in r)]

    if not rows:
        return []

    # 헤더 라인 찾기
    header_idx = 0
    for i in range(min(50, len(rows))):
        if rows[i] and str(rows[i][0]).strip().startswith("#"):
            header_idx = i
            break

    headers = [h.strip() for h in rows[header_idx]]

    # 데이터 시작 라인 (타입 정의 건너뛰기)
    data_start = header_idx + 1
    TYPE_TOKENS = {"int32", "uint16", "uint32", "sbyte", "byte", "str", "bit&01", "bit&02", "bit&04", "bit&08", "bit&10", "bit&20", "bit&40", "bit&80", "Row", "Image", "Map"}
    while data_start < len(rows):
        first = str(rows[data_start][0]).strip()
        if first in TYPE_TOKENS or first.startswith("bit&") or first == "":
            data_start += 1
            continue
        if _NUM_RE.match(first):
            break
        data_start += 1

    out = []
    for r in rows[data_start:]:
        item = {}
        for i, v in enumerate(r):
            if i >= len(headers):
                break
            key = headers[i]
            item[key] = v.strip() if isinstance(v, str) else v
        
        # 키 컬럼(#)이 비어있으면 스킵
        if "#" in item and str(item["#"]).strip() == "":
            continue
        out.append(item)

    return out


def build():
    print(">>> 데이터 로딩을 시작합니다...")

    # 현재 작업 디렉토리 (파일이 여기 있다고 가정)
    CWD = os.getcwd()

    # 로드: 폴더 구조가 안 맞으면 현재 폴더에서 찾도록 수정
    print(" - PlaceName & Weather 로딩 중...")
    placename_en_rows = read_ffxiv_table(os.path.join(RAW_EN_DIR, "PlaceName.csv"), os.path.join(CWD, "PlaceName.csv"))
    placename_ko_rows = read_ffxiv_table(os.path.join(RAW_KO_DIR, "PlaceName.csv"), os.path.join(CWD, "PlaceName.csv"))
    weather_en_rows = read_ffxiv_table(os.path.join(RAW_EN_DIR, "Weather.csv"), os.path.join(CWD, "Weather.csv"))
    weather_ko_rows = read_ffxiv_table(os.path.join(RAW_KO_DIR, "Weather.csv"), os.path.join(CWD, "Weather.csv"))

    places_en = {to_int_ref(r.get("#")): (r.get("Name") or "").strip() for r in placename_en_rows if to_int_ref(r.get("#")) > 0}
    places_ko = {to_int_ref(r.get("#")): (r.get("Name") or "").strip() for r in placename_ko_rows if to_int_ref(r.get("#")) > 0}

    # [수정 1] 이름으로 ID를 찾기 위한 역참조 맵 생성 (PlaceName이 텍스트로 되어 있는 경우 대비)
    reverse_places = {}
    # 한국어 이름 우선 등록
    for pid, name in places_ko.items():
        if name: reverse_places[name] = pid
    # 영어 이름 등록 (필요시)
    for pid, name in places_en.items():
        if name: reverse_places[name] = pid

    weathers_en = {to_int_ref(r.get("#")): (r.get("Name") or "").strip() for r in weather_en_rows if to_int_ref(r.get("#")) > 0}
    weathers_ko = {to_int_ref(r.get("#")): (r.get("Name") or "").strip() for r in weather_ko_rows if to_int_ref(r.get("#")) > 0}

    print(" - TerritoryType & WeatherRate 로딩 중...")
    territories = read_ffxiv_table(os.path.join(RAW_EN_DIR, "TerritoryType.csv"), os.path.join(CWD, "TerritoryType.csv"))
    weather_rate_rows = read_ffxiv_table(os.path.join(RAW_EN_DIR, "WeatherRate.csv"), os.path.join(CWD, "WeatherRate.csv"))
    weather_rates = {to_int_ref(r.get("#")): r for r in weather_rate_rows if to_int_ref(r.get("#")) > 0}

    valid_zones = []
    used_weather_ids = set()

    print(">>> 데이터 처리 및 필터링 중...")

    for t in territories:
        t_id = to_int_ref(t.get("#"), 0)
        if t_id <= 0:
            continue

        usage = to_int_ref(t.get("TerritoryIntendedUse", -1), -1)
        cf_cond = to_int_ref(t.get("ContentFinderCondition", 0), 0)

        # [수정 2] PlaceName 파싱 로직 개선
        place_val = t.get("PlaceName", 0)
        place_id = to_int_ref(place_val, 0)
        
        # ID 추출 실패(0)했고 값이 텍스트라면 역참조 맵에서 ID 검색
        if place_id == 0 and isinstance(place_val, str):
            place_id = reverse_places.get(place_val.strip(), 0)

        w_rate_id = to_int_ref(t.get("WeatherRate", 0), 0)

        # [수정 3] 필터 조건 완화 (60: 퀘스트 배틀/부족 퀘스트 지역 포함)
        # 행성 파엔나, 오이지스는 usage가 60입니다.
        if usage not in [0, 1, 60]:
            continue
            
        if cf_cond != 0:
            continue
        if place_id <= 0 or w_rate_id <= 0:
            continue

        name_en = (places_en.get(place_id, "") or "").strip()
        name_ko = (places_ko.get(place_id, "") or "").strip()
        
        # 이름이 없으면 역참조로 찾은 이름이라도 사용 시도 (현재 CSV에 있는 값)
        if not name_ko and isinstance(place_val, str) and not place_val.isdigit():
             name_ko = place_val
        
        if not name_en and name_ko: # 영문명이 없으면 한글명으로 대체 (또는 그 반대)
             name_en = name_ko

        if not name_en or not name_ko:
            continue
        if name_en.isdigit(): # 이름이 숫자로만 되어있으면 더미 데이터일 확률 높음
            continue

        rate_row = weather_rates.get(w_rate_id)
        if not rate_row:
            continue

        list_en = []
        list_ko = []
        cumulative = 0

        for i in range(8):
            w_id = to_int_ref(rate_row.get(f"Weather[{i}]"), 0)
            rate = to_int_ref(rate_row.get(f"Rate[{i}]"), 0)

            if w_id <= 0 or rate <= 0:
                break

            cumulative += rate
            if cumulative > 100:
                cumulative = 100

            used_weather_ids.add(w_id)

            w_name_en = weathers_en.get(w_id, f"Unknown_{w_id}")
            w_name_ko = weathers_ko.get(w_id, f"Unknown_{w_id}")

            list_en.append(w_name_en)
            list_en.append(cumulative)
            list_ko.append(w_name_ko)
            list_ko.append(cumulative)

            if cumulative >= 100:
                break

        if not list_en or not list_ko:
            continue

        valid_zones.append({
            "territory_id": t_id,
            "place_id": place_id,
            "weather_rate_id": w_rate_id,
            "name_en": name_en,
            "name_ko": name_ko,
            "list_en": list_en,
            "list_ko": list_ko,
        })

    valid_zones.sort(key=lambda x: x["territory_id"])

    print(f">>> 총 {len(valid_zones)}개의 유효 지역 추출 완료.")
    print(">>> JSON 파일(weather_data.json) 생성 중...")
    
    # ... (이하 JSON 생성 코드는 기존과 동일) ...
    output_json = {
        "weather_rates": {"en": {}, "ko": {}},
        "weather_rates_by_territory": {},
        "info": {"zones": {}, "weather": {}}
    }

    for z in valid_zones:
        output_json["weather_rates"]["en"][z["name_en"]] = z["list_en"]
        output_json["weather_rates"]["ko"][z["name_ko"]] = z["list_ko"]

    for z in valid_zones:
        tid = str(z["territory_id"])
        output_json["weather_rates_by_territory"][tid] = {
            "place_id": z["place_id"],
            "weather_rate_id": z["weather_rate_id"],
            "en": z["list_en"],
            "ko": z["list_ko"],
        }
        output_json["info"]["zones"][tid] = {
            "PlaceID": z["place_id"],
            "WeatherRateID": z["weather_rate_id"],
            "En": z["name_en"],
            "Ko": z["name_ko"],
        }

    for w_id in sorted(used_weather_ids):
        output_json["info"]["weather"][str(w_id)] = {
            "En": weathers_en.get(w_id, f"Unknown_{w_id}"),
            "Ko": weathers_ko.get(w_id, f"Unknown_{w_id}"),
        }

    out_json_path = os.path.join(OUTPUT_DIR, "weather_data.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    print(">>> 모든 작업 완료!")
    print(f"생성된 파일: {out_json_path}")

if __name__ == "__main__":
    build()