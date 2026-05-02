# services/ffxiv/tug_db.py (또는 네 tug_db.py 위치)
import json
from services.ffxiv.weather_data_loader import load_weather_maps
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

def _to_float(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "" or s.lower() == "null":
        return None
    return float(s)

def _to_int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None

def _to_int_seconds(v) -> Optional[int]:
    # intuitionLength가 "null"/null/숫자 섞여 있어서 안전 처리
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().lower()
    if s == "" or s == "null":
        return None
    try:
        return int(float(s))
    except Exception:
        return None

def _et_hour_to_str(h: Optional[float]) -> str:
    if h is None:
        return "-"
    # 23.5 같은 값 대응
    hh = int(h) % 24
    mm = 30 if abs(h - int(h) - 0.5) < 1e-6 else 0
    return f"{hh:02d}:{mm:02d}"

def _format_et_range(start: Optional[float], end: Optional[float]) -> str:
    if start is None or end is None:
        return "-"
    # ✅ DB에 start=0,end=0 들어오는 케이스: 사실상 올데이로 처리(0~24)
    if float(start) == 0.0 and float(end) == 0.0:
        return "ET 00:00 ~ 24:00"
    return f"ET {_et_hour_to_str(start)} ~ {_et_hour_to_str(end)}"

def _tex_to_xivapi_png(tex_path: Optional[str]) -> Optional[str]:
    if not tex_path:
        return None

    p = str(tex_path).strip()
    if not p:
        return None

    # 이미 URL이면 prefix 제거
    if p.startswith("https://xivapi.com/"):
        p = p[len("https://xivapi.com/"):]

    p = p.lstrip("/")

    # .tex -> .png (끝에 있을 때만)
    if p.endswith(".tex"):
        p = p[:-4] + ".png"

    # ui/icon -> i
    p = p.replace("ui/icon/", "i/")

    return f"https://xivapi.com/{p}"

@dataclass
class FishEntry:
    fish_id: int
    name_ko: str
    desc: str
    bait_path: List[str]
    start: Optional[float]
    end: Optional[float]
    location_id: Optional[int]
    previous_weather: List[Any]  # 숫자 문자열 리스트일 수 있음
    weather: List[Any]
    intuition_length: Optional[int]
    is_teoju: bool
    icon_tex: Optional[str]
    fish_tex: Optional[str]

@dataclass
class SpotEntry:
    spot_id: int
    name: str
    continent: str
    region: str
    sub_region: str
    zone: str
    territory: str
    on_reach: str
    on_end: str

def _spot_key(spot: SpotEntry) -> str:
    # alerts에 쓸 안정 키
    return f"{spot.region}/{spot.sub_region}/{spot.name}"

class TugDB:
    """
    final_fishing_db.json layout:
      {
        "FISH": { "<fish_id_str>": {...} },
        "SPOTS": { "<spot_id_str>": {...} },
        "SPOTS_TREE": {...},
        "_meta": {...}
      }
    """

    def __init__(self, path: str, *, weather_types_path: str = "data/ffxiv/weather/weather_types.json"):
        with open(path, "r", encoding="utf-8") as f:
            self.raw = json.load(f)

        self.fish_raw: Dict[int, Dict[str, Any]] = {int(k): v for k, v in self.raw.get("FISH", {}).items()}
        self.spots_raw: Dict[int, Dict[str, Any]] = {int(k): v for k, v in self.raw.get("SPOTS", {}).items()}

        # ✅ 날씨 id/en/ko 로드 (auto from weather_data.json)
        try:
            maps = load_weather_maps()
            self.weather_id_to_ko: Dict[str, str] = dict(maps.get('id_to_ko', {}))
            self.weather_id_to_en: Dict[str, str] = dict(maps.get('id_to_en', {}))
            self.weather_en_to_ko: Dict[str, str] = dict(maps.get('en_to_ko', {}))
            self.weather_ko_to_en: Dict[str, str] = dict(maps.get('ko_to_en', {}))
        except Exception:
            self.weather_id_to_ko = {}
            self.weather_id_to_en = {}
            self.weather_en_to_ko = {}
            self.weather_ko_to_en = {}

    def get_fish(self, fish_id: int) -> Optional[FishEntry]:
        v = self.fish_raw.get(int(fish_id))
        if not v:
            return None

        # ✅ 새 DB: icon_tex/fish_tex, 구 DB: icon_teoju(터주 전용 아이콘)도 섞여있을 수 있어 둘 다 대응
        icon_tex = v.get("icon_tex") or v.get("icon_teoju")
        fish_tex = v.get("fish_tex") or v.get("icon_teoju")  # 어탁/큰 아이콘으로 쓰고 싶으면 이쪽 우선

        return FishEntry(
            fish_id=int(fish_id),
            name_ko=(v.get("name_ko") or "").strip(),
            desc=v.get("desc") or "",
            bait_path=list(v.get("bait_path") or []),
            start=_to_float(v.get("start")),
            end=_to_float(v.get("end")),
            location_id=_to_int(v.get("location_id")),
            previous_weather=list(v.get("previousWeatherSet") or []),
            weather=list(v.get("weatherSet") or []),
            intuition_length=_to_int_seconds(v.get("intuitionLength")),
            is_teoju=bool(v.get("is_teoju", False)),
            icon_tex=icon_tex,
            fish_tex=fish_tex,
        )

    def list_teoju_ids_by_territory(self, territory_ko: str, limit: int = 30) -> list[int]:
        """
        territory_ko: 예) '커르다스 서부고지', '아짐 대초원'
        return: fish_id list (teoju only)
        """
        territory_ko = (territory_ko or "").strip()
        if not territory_ko:
            return []

        out: list[int] = []

        # fish_raw: {fish_id:int -> dict}
        for fish_id, v in self.fish_raw.items():
            try:
                if not bool(v.get("is_teoju", False)):
                    continue

                loc_id = v.get("location_id")
                if loc_id is None:
                    continue

                spot = self.get_spot(int(loc_id))
                if not spot or self._is_special_spot(spot):
                    continue

                if str(spot.territory).strip() != territory_ko:
                    continue

                out.append(int(fish_id))
                if len(out) >= limit:
                    break
            except Exception:
                continue

        return out

    def get_spot(self, spot_id: int) -> Optional[SpotEntry]:
        v = self.spots_raw.get(int(spot_id))
        if not v:
            return None
        return SpotEntry(
            spot_id=int(spot_id),
            name=(v.get("name") or "").strip(),
            continent=(v.get("continent") or "").strip(),
            region=(v.get("region") or "").strip(),
            sub_region=(v.get("sub_region") or "").strip(),
            zone=(v.get("zone") or "").strip(),
            territory=(v.get("territory") or "").strip(),
            on_reach=v.get("on_reach") or "",
            on_end=v.get("on_end") or "",
        )

    def _is_special_spot(self, spot: Optional[SpotEntry]) -> bool:
        """
        ✅ 이벤트/특수지역: SPOTS에 continent/region/... 가 "" 로 들어오는 케이스가 있음 → /터주에서는 제외
        """
        if not spot:
            return True
        # spot.name은 있는데 나머지가 비어있으면 특수지역으로 간주
        required = [spot.continent, spot.region, spot.sub_region, spot.zone, spot.territory]
        return any(x == "" for x in required)

    def _weather_ids_to_ko(self, ids: List[Any]) -> List[str]:
        out: List[str] = []
        for x in (ids or []):
            k = str(x).strip()
            if not k:
                continue
            if k.isdigit():
                out.append(self.weather_id_to_ko.get(k, k))
            else:
                out.append(self.weather_en_to_ko.get(k, k))
        return out

    def fish_search(self, q: str, limit: int = 25) -> List[Tuple[int, str]]:
        qq = (q or "").strip()
        if not qq:
            return []
        qq_low = qq.lower()
        out = []
        for fid, v in self.fish_raw.items():
            name = (v.get("name_ko") or "").strip()
            if qq_low in name.lower():
                out.append((fid, name))
                if len(out) >= limit:
                    break
        return out

    def _tex_to_xivapi_png(tex_path: Optional[str]) -> Optional[str]:
        """
        XIVAPI의 404 에러를 방지하기 위해 경로를 'i/'로 강제 변환합니다.
        """
        if not tex_path:
            return None
        
        p = str(tex_path).strip()
        
        # 1. 확장자 처리
        if p.endswith(".tex"):
            p = p[:-4] + ".png"
        
        # 2. XIVAPI 도메인 중복 제거 및 앞쪽 슬래시 정리
        p = p.replace("https://xivapi.com/", "")
        p = p.lstrip("/")

        # 3. 핵심: ui/icon/ 경로를 i/ 로 변환 (이게 안 되면 404가 뜹니다)
        if "ui/icon/" in p:
            p = p.replace("ui/icon/", "i/")
        elif p.startswith("ui/"):
            p = p.replace("ui/", "i/", 1)
            
        return "https://xivapi.com/" + p

    def build_display(self, fish_id: int, *, teoju_only: bool = True) -> Optional[Dict[str, Any]]:
        fish = self.get_fish(fish_id)
        if not fish:
            return None

        if teoju_only and not fish.is_teoju:
            return None

        spot = self.get_spot(fish.location_id) if fish.location_id else None
        if teoju_only and self._is_special_spot(spot):
            return None

        method_line = " → ".join([x for x in fish.bait_path if x]) if fish.bait_path else "-"

        prev_ko = self._weather_ids_to_ko(fish.previous_weather)
        cur_ko = self._weather_ids_to_ko(fish.weather)

        # 조건 라인: "A 또는 B → C 또는 D" / "C" / "-" 형태로
        left = " 또는 ".join(prev_ko) if prev_ko else ""
        right = " 또는 ".join(cur_ko) if cur_ko else ""
        if left and right:
            condition_line = f"{left} → {right}"
        elif right:
            condition_line = right
        else:
            condition_line = "-"

        time_line = _format_et_range(fish.start, fish.end)

        # ✅ 아이콘/어탁 이미지 URL
        thumb_url = _tex_to_xivapi_png(getattr(fish, "icon_tex", None))
        fish_img_url = _tex_to_xivapi_png(getattr(fish, "fish_tex", None))

        print("[TUGTHUMB]", thumb_url)
        print("[TUGIMG]", fish_img_url)
        # ✅ 위치 라인
        location_line = "-"
        if spot and not self._is_special_spot(spot):
            location_line = f"{spot.territory} - {spot.name}"

        return {
            "fish_id": fish.fish_id,
            "name_ko": fish.name_ko,
            "desc": fish.desc,
            "is_teoju": fish.is_teoju,
            "spot": spot,
            "spot_key": _spot_key(spot) if spot else None,
            "location_line": location_line,
            "time_line": time_line,
            "condition_line": condition_line,
            "method_line": method_line,
            "intuition_seconds": fish.intuition_length,
            "thumb_url": thumb_url,
            "fish_img_url": fish_img_url,
            "fish": fish,
            "spot": spot,
        }