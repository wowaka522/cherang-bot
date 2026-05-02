# services/ffxiv/weather_logic.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import json
import re
import time

# ============================================================
# Paths
# ============================================================

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]  # .../services/ffxiv -> project root
DATA_DIR = PROJECT_ROOT / "data" / "ffxiv" / "weather" / "compiled"

WEATHER_DATA_PATH = DATA_DIR / "weather_data.json"
ZONE_ALIASES_PATH = PROJECT_ROOT / "data" / "ffxiv" / "weather" / "zone_aliases.json"

# 8 ET hours = 175 sec real-time per ET hour => 8 * 175 seconds per weather window
WEATHER_WINDOW_MS = 8 * 175 * 1000


# ============================================================
# Normalization
# ============================================================

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[·\.\,\-\_\(\)\[\]\{\}]+")
def norm(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def _safe_read_json(path: Path) -> Optional[Any]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ============================================================
# Loaded data (weather names / zone names / aliases / rates)
# ============================================================

# weather maps
WEATHER_KO: Dict[str, str] = {}        # EN weather -> KO weather
KO2EN: Dict[str, str] = {}             # KO weather -> EN weather

# zone maps
ZONE_EN_TO_KO: Dict[str, str] = {}     # EN zone -> KO zone
ZONE_KO_TO_EN: Dict[str, str] = {}     # norm(KO zone) -> EN zone

# alias maps (ko alias -> en zone)
ALIAS_KO2EN: Dict[str, str] = {}

# legacy flattened rate table:
# DATA[zone_en] = ["Clear Skies", 20, "Fair Skies", 40, ...] (threshold cumulative)
DATA: Dict[str, List[Any]] = {}
ZONES: List[str] = []

WEATHER_ID_TO_EN: dict[int, str] = {}
WEATHER_ID_TO_KO: dict[int, str] = {}

def _build_DATA_from_weather_data(weather_data: dict) -> Dict[str, List[Any]]:
    """
    Supports:
      A) weather_rates["en"][zone] = ["Clouds",20,"Clear Skies",50,...]  (flattened)
      B) weather_rates["en"][zone] = [[name, threshold], ...]            (pairs)
      C) weather_rates["en"][zone] = [{"name":..., "threshold":...}, ...] (dict pairs)
    Returns legacy flattened DATA format.
    """
    wr = (weather_data or {}).get("weather_rates", {})
    if not isinstance(wr, dict):
        return {}

    rates_dict = wr.get("en") if isinstance(wr.get("en"), dict) else wr
    if not isinstance(rates_dict, dict):
        return {}

    out: Dict[str, List[Any]] = {}

    for zone, pairs in rates_dict.items():
        # Case A: already flattened list
        if isinstance(pairs, list) and pairs:
            is_flat = True
            for i, v in enumerate(pairs):
                if i % 2 == 0 and not isinstance(v, str):
                    is_flat = False
                    break
                if i % 2 == 1 and not isinstance(v, int):
                    is_flat = False
                    break
            if is_flat and len(pairs) % 2 == 0:
                out[str(zone)] = list(pairs)
                continue

        # Case B/C: list of pairs
        flat: List[Any] = []
        if isinstance(pairs, list):
            for pair in pairs:
                name = None
                thr = None
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    name, thr = pair[0], pair[1]
                elif isinstance(pair, dict):
                    name, thr = pair.get("name"), pair.get("threshold")

                if name is None or thr is None:
                    continue
                flat.append(str(name))
                flat.append(int(thr))

        if flat:
            out[str(zone)] = flat

    return out


def _load_all() -> None:
    global DATA, ZONES

    wd = _safe_read_json(WEATHER_DATA_PATH)
    if not isinstance(wd, dict):
        return

    # 1) build DATA + ZONES
    try:
        DATA = _build_DATA_from_weather_data(wd)
        ZONES = list(DATA.keys())
    except Exception:
        DATA = {}
        ZONES = []

    # 2) info maps
    info = wd.get("info") or {}
    weathers = info.get("weather") or {}
    zones = info.get("zones") or {}

    # ---- weather: dict 형태가 정석 (너 파일은 이거)
    if isinstance(weathers, dict):
        for k, v in weathers.items():
            try:
                wid = int(k)
                if not isinstance(v, dict):
                    continue
                en = str(v.get("En") or v.get("en") or "").strip()
                ko = str(v.get("Ko") or v.get("ko") or "").strip()

                if en:
                    WEATHER_ID_TO_EN[wid] = en
                if ko:
                    WEATHER_ID_TO_KO[wid] = ko
                if en and ko:
                    WEATHER_KO[en] = ko
                    KO2EN[norm(ko)] = en
            except Exception:
                pass

    # (호환) list 형태도 지원
    elif isinstance(weathers, list):
        for w in weathers:
            try:
                if not isinstance(w, dict):
                    continue
                wid = int(w.get("id"))
                en = str(w.get("En") or w.get("en") or "").strip()
                ko = str(w.get("Ko") or w.get("ko") or "").strip()

                if en:
                    WEATHER_ID_TO_EN[wid] = en
                if ko:
                    WEATHER_ID_TO_KO[wid] = ko
                if en and ko:
                    WEATHER_KO[en] = ko
                    KO2EN[norm(ko)] = en
            except Exception:
                pass

    # ---- zones: dict 형태가 정석 (너 파일은 이거)
    if isinstance(zones, dict):
        for _k, v in zones.items():
            try:
                if not isinstance(v, dict):
                    continue
                en = str(v.get("En") or v.get("en") or "").strip()
                ko = str(v.get("Ko") or v.get("ko") or "").strip()
                if en and ko:
                    ZONE_EN_TO_KO[en] = ko
                    ZONE_KO_TO_EN.setdefault(norm(ko), en)
            except Exception:
                pass

    # (호환) list 형태도 지원
    elif isinstance(zones, list):
        for z in zones:
            try:
                if not isinstance(z, dict):
                    continue
                en = str(z.get("En") or z.get("en") or "").strip()
                ko = str(z.get("Ko") or z.get("ko") or "").strip()
                if en and ko:
                    ZONE_EN_TO_KO[en] = ko
                    ZONE_KO_TO_EN.setdefault(norm(ko), en)
            except Exception:
                pass

    # 3) aliases
    za = _safe_read_json(ZONE_ALIASES_PATH)
    if isinstance(za, dict):
        for ko_alias, en_zone in za.items():
            try:
                ko_alias_s = str(ko_alias).strip()
                en_zone_s = str(en_zone).strip()
                if ko_alias_s and en_zone_s:
                    ALIAS_KO2EN[ko_alias_s] = en_zone_s
            except Exception:
                pass


_load_all()


# ============================================================
# Forecast algorithm (FFXIV standard)
# ============================================================

def calculate_forecast_target(timestamp_ms: int) -> int:
    unix = timestamp_ms // 1000
    bell = unix // 175
    increment = (bell + 8 - (bell % 8)) % 24
    total_days = unix // 4200
    calc_base = total_days * 0x64 + increment
    step1 = ((calc_base << 0xB) ^ calc_base) & 0xFFFFFFFF
    step2 = ((step1 >> 8) ^ step1) & 0xFFFFFFFF
    return step2 % 0x64


# ============================================================
# Legacy-compatible public API (used by cogs/ffxiv/weather.py)
# ============================================================

def get_weather_at(zone: str, timestamp_ms: int) -> Optional[str]:
    """
    Returns EN weather string (e.g., "Fair Skies") or None if zone invalid.
    """
    zone_data = DATA.get(zone)
    if not zone_data:
        return None
    target = calculate_forecast_target(timestamp_ms)
    for i in range(0, len(zone_data) - 1, 2):
        weather_name = zone_data[i]
        prob = zone_data[i + 1]
        if target < prob:
            return str(weather_name)
    return str(zone_data[-1])


def get_weather(zone: str) -> Optional[str]:
    return get_weather_at(zone, int(time.time() * 1000))


def get_weather_icon_filename(en_weather: str) -> str:
    return (en_weather or "").replace(" ", "_") + ".png"


def to_korean_weather(en_weather: str) -> str:
    if not en_weather:
        return en_weather
    return WEATHER_KO.get(en_weather, en_weather)


def to_korean_zone(zone_key: str) -> str:
    """
    Prefer official zone map, else try alias reverse search, else return key.
    """
    if not zone_key:
        return zone_key
    if zone_key in ZONE_EN_TO_KO:
        return ZONE_EN_TO_KO[zone_key]
    # alias reverse (best effort)
    for ko, en in ALIAS_KO2EN.items():
        if en == zone_key:
            return ko
    return zone_key


def find_zone_matches(user_input: str) -> List[str]:
    """
    MUST be safe: always returns list[str]; never raises NameError.
    Matching order: alias(ko)->en, ko zone -> en, en zone contains -> en.
    """
    n = norm(user_input)
    if not n:
        return []

    # 1) aliases: if user input matches within alias key
    ko_alias_matches = [
        en for ko, en in ALIAS_KO2EN.items()
        if n in norm(ko)
    ]

    # 2) KO official zone names (from weather_data info.zones)
    ko_zone_matches = [
        en for ko_norm, en in ZONE_KO_TO_EN.items()
        if n in ko_norm
    ]

    # 3) EN zone names (prefer DATA keys if available)
    en_pool = ZONES if ZONES else list(ZONE_EN_TO_KO.keys())
    en_matches = [z for z in en_pool if n in norm(z)]

    # Merge, de-dup, keep stable order, then prefer shorter keys
    all_matches = list(dict.fromkeys(ko_alias_matches + ko_zone_matches + en_matches))
    all_matches.sort(key=len)
    return all_matches


def normalize_zone_key(user_input: str) -> Optional[str]:
    matches = find_zone_matches(user_input)
    return matches[0] if matches else None


def weather_id_from_any(name_or_id: Any) -> Optional[int]:
    """
    호환용: weather.py에서 안 쓰면 그냥 둬도 됨.
    (여긴 weather_id 개념이 없어도 되지만, 다른 서비스에서 쓸 수 있어서 유지)
    """
    if name_or_id is None:
        return None
    try:
        if isinstance(name_or_id, int):
            return int(name_or_id)
        s = str(name_or_id).strip()
        if s.isdigit():
            return int(s)
    except Exception:
        return None
    return None  # weather_id는 이 파일에서 핵심 아님


def normalize_weather_set(values: Sequence[Any]) -> List[str]:
    """
    입력이 id/en/ko 섞여 들어와도 weather.py에서 쓰기 편하게 EN 문자열로 맞춰주는 용도.
    (id는 여기선 의미 없으니, str은 KO2EN을 통해 EN으로 바꿈)
    """
    out: List[str] = []
    for v in values or []:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        # KO -> EN
        en = KO2EN.get(norm(s), s)
        out.append(en)
    return out


def et_ms(now_ms: Optional[int] = None) -> int:
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    return int(now_ms * (3600 / 175))


def et_hours(now_ms: Optional[int] = None) -> float:
    ms = et_ms(now_ms)
    hours = (ms / 1000.0) / 3600.0
    return hours % 24.0


def is_in_et_window(start_et: Optional[float], end_et: Optional[float], now_et: float) -> bool:
    if start_et is None or end_et is None:
        return True
    start = float(start_et) % 24.0
    end = float(end_et) % 24.0
    now = float(now_et) % 24.0
    if start == end:
        return True
    if start < end:
        return start <= now < end
    return now >= start or now < end


def weather_matches(prev_set: Sequence[Any], cur_set: Sequence[Any], w_prev: Any, w_now: Any) -> bool:
    """
    True if:
      - prev_set empty OR w_prev matches one of prev_set
      - cur_set empty OR w_now matches one of cur_set
    Inputs can be EN/KO strings.
    """
    prev_en = set(normalize_weather_set(prev_set))
    cur_en = set(normalize_weather_set(cur_set))

    wprev = KO2EN.get(norm(str(w_prev)), str(w_prev)) if w_prev is not None else None
    wnow = KO2EN.get(norm(str(w_now)), str(w_now)) if w_now is not None else None

    ok_prev = True if not prev_en else (wprev in prev_en)
    ok_now = True if not cur_en else (wnow in cur_en)
    return ok_prev and ok_now