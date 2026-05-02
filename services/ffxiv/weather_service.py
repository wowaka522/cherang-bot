# services/ffxiv/weather_service.py
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from services.ffxiv import weather_logic as wl
from services.ffxiv.weather_logic import (
    WEATHER_WINDOW_MS,
    find_zone_matches,
    get_weather_at,
    to_korean_zone,
    to_korean_weather,
    get_weather_icon_filename,
)

try:
    from cogs.quest import quest_progress_add
except Exception:
    def quest_progress_add(*args, **kwargs):
        return None


def _normalize_zone_match(ret):
    """
    find_zone_matches() 반환 포맷이 버전마다 달라질 수 있어 안전하게 파싱.
    """
    if isinstance(ret, dict):
        cand = ret.get("all_matches") or ret.get("matches") or ret.get("results") or []
        if cand and isinstance(cand[0], dict):
            z = cand[0]
            return z.get("zone_key"), z.get("zone_ko"), z.get("similar")
        return None, None, None

    if isinstance(ret, list) and ret:
        first = ret[0]
        if isinstance(first, dict):
            return first.get("zone_key"), first.get("zone_ko"), first.get("similar")
        if isinstance(first, str):
            return first, None, None
        return None, None, None

    if isinstance(ret, str):
        return ret, None, None

    return None, None, None


def _normalize_weather_input_ko(s: str) -> str:
    t = (s or "").strip()
    if t in ("자기장 폭풍", "자기장폭풍"):
        return "자기 폭풍"
    return t


@dataclass
class ZoneResolveResult:
    zone_key: str | None
    candidates: list[str]


class WeatherService:
    """
    - zone alias 적용 + fuzzy resolve
    - /날씨, /날씨찾기 계산
    - 터주용 conditions(ok_now / next_ts) 계산
    """

    ET_MS_PER_HOUR = 175000  # 1 ET hour = 175 seconds = 175000 ms

    def __init__(self, bot):
        self.bot = bot
        self._zone_aliases: dict | None = None

    # ---------- text ----------
    def t(self, key: str, **kwargs) -> str:
        """
        - bot.texts.t(...)가 'format'을 안 해주는 경우가 있어서
        최종 문자열에 대해 여기서 한 번 더 format을 보장한다.
        """
        bot = getattr(self, "bot", None)
        texts = getattr(bot, "texts", None) if bot else None

        s = None
        if texts and hasattr(texts, "t"):
            try:
                s = texts.t(key, **kwargs)
            except Exception:
                s = None

        if not s:
            s = str(key)

        # ✅ 무조건 format 한 번 더 시도 (실패하면 원문 유지)
        if kwargs:
            try:
                s = s.format(**kwargs)
            except Exception:
                pass

        return s

    # ---------- zone aliases ----------
    def _load_zone_aliases(self) -> dict:
        if isinstance(self._zone_aliases, dict):
            return self._zone_aliases

        path = os.path.join("data", "text", "ffxiv", "zone_aliases.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._zone_aliases = json.load(f) or {}
        except Exception:
            self._zone_aliases = {}
        return self._zone_aliases

    def normalize_zone_input(self, user_text: str) -> str:
        raw = (user_text or "").strip()
        compact = raw.replace(" ", "")
        aliases = self._load_zone_aliases()

        if compact in aliases:
            return aliases[compact]
        return aliases.get(raw, raw)

    # ---------- resolve ----------
    def resolve_zone(self, zone_input: str) -> ZoneResolveResult:
        zone_input = self.normalize_zone_input(zone_input)
        ret = find_zone_matches(zone_input)
        zone_key, _zone_ko, _similar = _normalize_zone_match(ret)

        candidates: list[str] = []
        if isinstance(ret, list):
            if ret and isinstance(ret[0], str):
                candidates = ret
            elif ret and isinstance(ret[0], dict):
                candidates = [
                    (z.get("zone_key") or z.get("key"))
                    for z in ret
                    if isinstance(z, dict) and (z.get("zone_key") or z.get("key"))
                ]
        elif isinstance(ret, dict):
            cand = ret.get("all_matches") or ret.get("matches") or ret.get("results") or []
            if cand and isinstance(cand[0], dict):
                candidates = [
                    (z.get("zone_key") or z.get("key"))
                    for z in cand
                    if isinstance(z, dict) and (z.get("zone_key") or z.get("key"))
                ]
        elif isinstance(ret, str):
            candidates = [ret]

        candidates = [c for c in candidates if isinstance(c, str)]

        # ✅ 여기만 바뀜: zone_key가 있으면 candidates가 많아도 그대로 반환
        if zone_key:
            return ZoneResolveResult(zone_key=zone_key, candidates=candidates)

        return ZoneResolveResult(zone_key=None, candidates=candidates)

    # ---------- weather helpers ----------
    def zone_possible_weathers_ko(self, zone_key: str) -> set[str]:
        raw = wl.DATA.get(zone_key) or []
        out: set[str] = set()
        for i in range(0, len(raw), 2):
            w = raw[i]
            if isinstance(w, str):
                out.add(to_korean_weather(w) or w)
        return out

    def suggest_zones_for_weather_ko(self, target_ko: str, limit: int = 5) -> list[str]:
        hits: list[str] = []
        for zk in wl.ZONES:
            if target_ko in self.zone_possible_weathers_ko(zk):
                hits.append(to_korean_zone(zk) or zk)
                if len(hits) >= limit:
                    break
        return hits

    def normalize_weather_input_ko(self, s: str) -> str:
        return _normalize_weather_input_ko(s)

    # ---------- /날씨 ----------
    def build_now_payload(self, *, zone_key: str, user_id: int | None = None) -> dict:
        zone_ko = to_korean_zone(zone_key) or zone_key

        now_ms = int(time.time() * 1000)
        ts = now_ms - (now_ms % WEATHER_WINDOW_MS)

        w_now = get_weather_at(zone_key, ts)
        w_next = get_weather_at(zone_key, ts + WEATHER_WINDOW_MS)
        w_after = get_weather_at(zone_key, ts + WEATHER_WINDOW_MS * 2)

        if not w_now:
            return {"ok": False, "zone_ko": zone_ko}

        w_now_ko = to_korean_weather(w_now) or w_now
        w_next_ko = to_korean_weather(w_next) or w_next
        w_after_ko = to_korean_weather(w_after) or w_after

        remain_ms = WEATHER_WINDOW_MS - (now_ms % WEATHER_WINDOW_MS)
        remain_sec = max(0, int(remain_ms // 1000))
        mm, ss = divmod(remain_sec, 60)
        left_text = f"{mm:02d}:{ss:02d}"
        et_hour = int((now_ms / self.ET_MS_PER_HOUR) % 24)

        # quest progress (optional)
        if user_id is not None:
            quest_progress_add(
                user_id,
                "weather_check",
                1,
                payload={"zone_key": zone_key, "zone_ko": zone_ko, "weather_ko": w_now_ko, "et_hour": et_hour},
            )

        icon_filename = get_weather_icon_filename(w_now) if w_now else None
        icon_path = os.path.join("assets", "weather_icons", icon_filename) if icon_filename else None

        return {
            "ok": True,
            "zone_ko": zone_ko,
            "w_now_ko": w_now_ko,
            "w_next_ko": w_next_ko,
            "w_after_ko": w_after_ko,
            "left_text": left_text,
            "et_hour": et_hour,
            "icon_path": icon_path,
        }

    # ---------- /날씨찾기 ----------
    def _find_first_target_within_24h(self, zone_key: str, target_ko: str) -> int | None:
        now_ms = int(time.time() * 1000)
        ts = now_ms - (now_ms % WEATHER_WINDOW_MS)

        max_steps = int((24 * 60 * 60 * 1000) / WEATHER_WINDOW_MS) + 2
        for _ in range(max_steps):
            w = get_weather_at(zone_key, ts)
            w_ko = to_korean_weather(w) if w else None
            if w_ko == target_ko:
                return int(ts // 1000)
            ts += WEATHER_WINDOW_MS
        return None

    def build_find_payload(self, *, zone_key: str, target_ko: str) -> dict:
        zone_ko = to_korean_zone(zone_key) or zone_key

        possible = self.zone_possible_weathers_ko(zone_key)
        if target_ko not in possible:
            suggests = self.suggest_zones_for_weather_ko(target_ko, limit=5)

            msg = self.t("weather.find.impossible", zone_ko=zone_ko, target_ko=target_ko)

            # 추가 안내
            if possible:
                msg += "\n" + self.t(
                    "weather.find.available_in_zone",
                    weathers=", ".join(sorted(possible))
                )

            if suggests:
                msg += "\n" + self.t("weather.find.suggest", zones=" / ".join(suggests))
            else:
                msg += "\n" + self.t("weather.find.suggest.none")

            msg += "\n" + self.t("weather.find.tip.retry")

            return {"ok": False, "kind": "impossible", "content": msg}

# services/ffxiv/weather_service.py 안 build_find_payload()

        next_ts = self._find_first_target_within_24h(zone_key, target_ko)
        if not next_ts:
            return {
                "ok": False,
                "kind": "fail",
                "content": self.t("weather.find.msg.not_found_24h", zone_ko=zone_ko, weather_ko=target_ko),
            }

        # ✅ 여기부터 교체
        unix = int(next_ts)  # seconds
        et_hour = int(((unix * 1000) / self.ET_MS_PER_HOUR) % 24)

        return {
            "ok": True,
            "zone_ko": zone_ko,
            "weather_ko": target_ko,
            "unix": unix,
            "et_hour": et_hour,
        }

    # ---------- forecast list (for [🔍 일기 예보]) ----------
    def build_forecast_list_payload(self, *, zone_key: str, windows: int = 12) -> dict:
        """
        windows: 보여줄 WEATHER_WINDOW 개수 (기본 12 = 앞으로 12윈도우)
        """
        zone_ko = to_korean_zone(zone_key) or zone_key

        now_ms = int(time.time() * 1000)
        base = now_ms - (now_ms % WEATHER_WINDOW_MS)

        rows: list[dict] = []
        for i in range(max(1, int(windows))):
            ts = base + WEATHER_WINDOW_MS * i
            w = get_weather_at(zone_key, ts)
            if not w:
                continue
            w_ko = to_korean_weather(w) or w

            start_unix = int(ts // 1000)
            end_unix = int((ts + WEATHER_WINDOW_MS) // 1000)

            # ET hour at window start (0~23)
            et_hour = int((ts / self.ET_MS_PER_HOUR) % 24)

            rows.append(
                {
                    "start_unix": start_unix,
                    "end_unix": end_unix,
                    "weather_ko": w_ko,
                    "et_hour": et_hour,
                }
            )

        if not rows:
            return {"ok": False, "zone_ko": zone_ko, "rows": []}

        return {"ok": True, "zone_ko": zone_ko, "rows": rows}


    # ===== Tug/Alert support (conditions) =====
    def _et_float_at_ms(self, ts_ms: int) -> float:
        return (ts_ms / self.ET_MS_PER_HOUR) % 24.0

    def _et_in_window(self, now_et: float, start_et: float | None, end_et: float | None) -> bool:
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

    def _offset_ms_to_et_window(self, et_start: float, start_et: float | None, end_et: float | None) -> int | None:
        if start_et is None or end_et is None:
            return 0

        start = float(start_et) % 24.0
        end = float(end_et) % 24.0
        e = float(et_start) % 24.0

        if start == end:
            return 0

        def in_window(x: float) -> bool:
            if start < end:
                return start <= x < end
            return x >= start or x < end

        if in_window(e):
            return 0

        diff_h = (start - e) % 24.0
        off_ms = int(round(diff_h * self.ET_MS_PER_HOUR))
        if 0 <= off_ms < WEATHER_WINDOW_MS:
            return off_ms
        return None

    def _norm_weather_to_en(self, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None

        if s.isdigit():
            try:
                wid = int(s)
                m = getattr(wl, "WEATHER_ID_TO_EN", None)
                if isinstance(m, dict) and wid in m:
                    return m[wid]
            except Exception:
                pass
            return None

        ko2en = getattr(wl, "KO2EN", None)
        if isinstance(ko2en, dict):
            n = wl.norm(s) if hasattr(wl, "norm") else s.lower()
            en = ko2en.get(n)
            if en:
                return en

        return s

    def _normalize_zone_key_for_conditions(self, zone_key: str) -> str | None:
        if zone_key in wl.DATA:
            return zone_key

        try:
            nz = getattr(wl, "normalize_zone_key", None)
            if callable(nz):
                z2 = nz(zone_key)
                if z2 and z2 in wl.DATA:
                    return z2
        except Exception:
            pass

        try:
            ret = find_zone_matches(zone_key)
            z2, _a, _b = _normalize_zone_match(ret)
            if z2 and z2 in wl.DATA:
                return z2
        except Exception:
            pass

        return None

    def is_now_available_for_conditions(
        self,
        *,
        zone_key: str,
        prev_set: list | None,
        cur_set: list | None,
        start_et: float | None,
        end_et: float | None,
    ) -> bool:
        prev_set = prev_set or []
        cur_set = cur_set or []

        zone_key2 = self._normalize_zone_key_for_conditions(zone_key)
        if not zone_key2:
            return False
        zone_key = zone_key2

        prev_en = [self._norm_weather_to_en(x) for x in prev_set]
        cur_en = [self._norm_weather_to_en(x) for x in cur_set]
        prev_en = [x for x in prev_en if x]
        cur_en = [x for x in cur_en if x]

        if prev_set and not prev_en:
            return False
        if cur_set and not cur_en:
            return False

        now_ms = int(time.time() * 1000)
        ts = now_ms - (now_ms % WEATHER_WINDOW_MS)

        w_prev = get_weather_at(zone_key, ts - WEATHER_WINDOW_MS)
        w_now = get_weather_at(zone_key, ts)

        if cur_en and (w_now not in cur_en):
            return False
        if prev_en and (w_prev not in prev_en):
            return False

        et_hour_now = (now_ms / self.ET_MS_PER_HOUR) % 24.0
        return self._et_in_window(et_hour_now, start_et, end_et)

    def _weather_match_at_window_ms(
        self,
        *,
        zone_key: str,
        window_ms: int,
        prev_set: list | None,
        cur_set: list | None,
    ) -> bool:
        prev_set = prev_set or []
        cur_set = cur_set or []

        zone_key2 = self._normalize_zone_key_for_conditions(zone_key)
        if not zone_key2:
            return False
        zone_key = zone_key2

        prev_en = [self._norm_weather_to_en(x) for x in prev_set]
        cur_en = [self._norm_weather_to_en(x) for x in cur_set]
        prev_en = [x for x in prev_en if x]
        cur_en = [x for x in cur_en if x]

        if prev_set and not prev_en:
            return False
        if cur_set and not cur_en:
            return False

        w_prev = get_weather_at(zone_key, int(window_ms) - WEATHER_WINDOW_MS)
        w_cur = get_weather_at(zone_key, int(window_ms))

        if cur_en and (w_cur not in cur_en):
            return False
        if prev_en and (w_prev not in prev_en):
            return False

        return True

    def get_next_window_ts_for_conditions(
        self,
        *,
        zone_key: str,
        prev_set: list | None,
        cur_set: list | None,
        start_et: float | None,
        end_et: float | None,
        horizon_hours: int = 24 * 30,
        include_now: bool = True,
    ) -> int | None:
        """
        Return the next epoch-seconds timestamp when conditions match.
        - include_now=True: if conditions are satisfied right now, return now.
        - include_now=False: skip the current window if it's already satisfied now,
        and return the next future occurrence.
        """

        # ✅ zone_key 정규화(한국어/별칭/오타 → 내부 key로)
        if zone_key not in wl.DATA:
            ret = find_zone_matches(zone_key)
            zone_key2, _zone_ko2, _similar2 = _normalize_zone_match(ret)
            if zone_key2:
                zone_key = zone_key2
        if zone_key not in wl.DATA:
            return None

        prev_set = prev_set or []
        cur_set = cur_set or []

        now_ms = int(time.time() * 1000)

        # 현재 시각 기준으로 이미 가능 여부 판단
        now_ok = self.is_now_available_for_conditions(
            zone_key=zone_key,
            prev_set=prev_set,
            cur_set=cur_set,
            start_et=start_et,
            end_et=end_et,
        )

        # include_now=True면 "지금"을 그대로 허용
        if now_ok and include_now:
            return int(now_ms // 1000)

        # 날씨 윈도우 기준으로 ts를 정렬
        ts = now_ms - (now_ms % WEATHER_WINDOW_MS)

        # include_now=False인데 지금 이미 가능하면, 현재 윈도우는 스킵하고 다음 윈도우부터 탐색
        if now_ok and (not include_now):
            ts += WEATHER_WINDOW_MS

        max_steps = int((horizon_hours * 60 * 60 * 1000) / WEATHER_WINDOW_MS) + 2

        for _ in range(max_steps):
            # 해당 윈도우의 prev/cur 날씨가 조건을 만족하는지 검사
            if not self._weather_match_at_window_ms(
                zone_key=zone_key,
                window_ms=ts,
                prev_set=prev_set,
                cur_set=cur_set,
            ):
                ts += WEATHER_WINDOW_MS
                continue

            # ET 시간대 조건이 있다면, 이 윈도우에서 들어갈 수 있는 offset을 계산
            et_start = self._et_float_at_ms(ts)
            off_ms = self._offset_ms_to_et_window(et_start, start_et, end_et)
            if off_ms is None:
                ts += WEATHER_WINDOW_MS
                continue

            cand_ms = ts + off_ms

            # include_now=False면, "지금/과거" 후보는 무조건 스킵하고 다음으로
            if (not include_now) and (cand_ms <= now_ms):
                ts += WEATHER_WINDOW_MS
                continue

            return int(cand_ms // 1000)

        return None