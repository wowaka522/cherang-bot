# services/ffxiv/weather_data_loader.py
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

DEFAULT_WEATHER_DATA_PATH = Path("data/ffxiv/weather/compiled/weather_data.json")


@lru_cache(maxsize=1)
def load_weather_data(path: str | None = None) -> Dict[str, Any]:
    p = Path(path) if path else DEFAULT_WEATHER_DATA_PATH
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_weather_maps(path: str | None = None) -> Dict[str, Dict[str, str]]:
    wd = load_weather_data(path)

    info_weather = wd.get("info", {}).get("weather", {})
    id_to_en = {str(k): v.get("En", "") for k, v in info_weather.items() if v.get("En")}
    id_to_ko = {str(k): v.get("Ko", "") for k, v in info_weather.items() if v.get("Ko")}
    en_to_ko = {v.get("En"): v.get("Ko") for v in info_weather.values() if v.get("En") and v.get("Ko")}
    ko_to_en = {v.get("Ko"): v.get("En") for v in info_weather.values() if v.get("En") and v.get("Ko")}

    zones = wd.get("info", {}).get("zones", {})
    zoneid_to_en = {str(k): v.get("En", "") for k, v in zones.items() if v.get("En")}
    zoneid_to_ko = {str(k): v.get("Ko", "") for k, v in zones.items() if v.get("Ko")}
    zone_en_to_ko = {v.get("En"): v.get("Ko") for v in zones.values() if v.get("En") and v.get("Ko")}
    zone_ko_to_en = {v.get("Ko"): v.get("En") for v in zones.values() if v.get("En") and v.get("Ko")}

    return {
        "id_to_en": id_to_en,
        "id_to_ko": id_to_ko,
        "en_to_ko": en_to_ko,
        "ko_to_en": ko_to_en,
        "zoneid_to_en": zoneid_to_en,
        "zoneid_to_ko": zoneid_to_ko,
        "zone_en_to_ko": zone_en_to_ko,
        "zone_ko_to_en": zone_ko_to_en,
    }
