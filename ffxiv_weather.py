# ffxiv_weather.py

import re
from time import time

DATA = {
    'Limsa Lominsa': ['Clouds', 20, 'Clear Skies', 50, 'Fair Skies', 80, 'Fog', 90, 'Rain'],
    'Middle La Noscea': ['Clouds', 20, 'Clear Skies', 50, 'Fair Skies', 70, 'Wind', 80, 'Fog', 90, 'Rain'],
    'Lower La Noscea': ['Clouds', 20, 'Clear Skies', 50, 'Fair Skies', 70, 'Wind', 80, 'Fog', 90, 'Rain'],
    'Eastern La Noscea': ['Fog', 5, 'Clear Skies', 50, 'Fair Skies', 80, 'Clouds', 90, 'Rain', 95, 'Showers'],
    'Western La Noscea': ['Fog', 10, 'Clear Skies', 40, 'Fair Skies', 60, 'Clouds', 80, 'Wind', 90, 'Gales'],
    'Upper La Noscea': ['Clear Skies', 30, 'Fair Skies', 50, 'Clouds', 70, 'Fog', 80, 'Thunder', 90, 'Thunderstorms'],
    'Outer La Noscea': ['Clear Skies', 30, 'Fair Skies', 50, 'Clouds', 70, 'Fog', 85, 'Rain'],
    'Mist': ['Clouds', 20, 'Clear Skies', 50, 'Fair Skies', 70, 'Fair Skies', 80, 'Fog', 90, 'Rain'],
    'Gridania': ['Rain', 5, 'Rain', 20, 'Fog', 30, 'Clouds', 40, 'Fair Skies', 55, 'Clear Skies', 85, 'Fair Skies'],
    'Central Shroud': ['Thunder', 5, 'Rain', 20, 'Fog', 30, 'Clouds', 40, 'Fair Skies', 55, 'Clear Skies', 85, 'Fair Skies'],
    'East Shroud': ['Thunder', 5, 'Rain', 20, 'Fog', 30, 'Clouds', 40, 'Fair Skies', 55, 'Clear Skies', 85, 'Fair Skies'],
    'South Shroud': ['Fog', 5, 'Thunderstorms', 10, 'Thunder', 25, 'Fog', 30, 'Clouds', 40, 'Fair Skies', 70, 'Clear Skies'],
    'North Shroud': ['Fog', 5, 'Showers', 10, 'Rain', 25, 'Fog', 30, 'Clouds', 40, 'Fair Skies', 70, 'Clear Skies'],
    'The Lavender Beds': ['Clouds', 5, 'Rain', 20, 'Fog', 30, 'Clouds', 40, 'Fair Skies', 55, 'Clear Skies', 85, 'Fair Skies'],
    'Ul\'dah': ['Clear Skies', 40, 'Fair Skies', 60, 'Clouds', 85, 'Fog', 95, 'Rain'],
    'Western Thanalan': ['Clear Skies', 40, 'Fair Skies', 60, 'Clouds', 85, 'Fog', 95, 'Rain'],
    'Central Thanalan': ['Dust Storms', 15, 'Clear Skies', 55, 'Fair Skies', 75, 'Clouds', 85, 'Fog', 95, 'Rain'],
    'Eastern Thanalan': ['Clear Skies', 40, 'Fair Skies', 60, 'Clouds', 70, 'Fog', 80, 'Rain', 85, 'Showers'],
    'Southern Thanalan': ['Heat Waves', 20, 'Clear Skies', 60, 'Fair Skies', 80, 'Clouds', 90, 'Fog'],
    'Northern Thanalan': ['Clear Skies', 5, 'Fair Skies', 20, 'Clouds', 50, 'Fog'],
    'The Goblet': ['Clear Skies', 40, 'Fair Skies', 60, 'Clouds', 85, 'Fog', 95, 'Rain'],
    'Ishgard': ['Snow', 60, 'Fair Skies', 70, 'Clear Skies', 75, 'Clouds', 90, 'Fog'],
    'Coerthas Central Highlands': ['Blizzards', 20, 'Snow', 60, 'Fair Skies', 70, 'Clear Skies', 75, 'Clouds', 90, 'Fog'],
    'Coerthas Western Highlands': ['Blizzards', 20, 'Snow', 60, 'Fair Skies', 70, 'Clear Skies', 75, 'Clouds', 90, 'Fog'],
    'Empyreum': ['Snow', 5, 'Fair Skies', 25, 'Clear Skies', 65, 'Clouds', 80, 'Fog'],
    'The Sea of Clouds': ['Clear Skies', 30, 'Fair Skies', 60, 'Clouds', 70, 'Fog', 80, 'Wind', 90, 'Umbral Wind'],
    'Azys Lla': ['Fair Skies', 35, 'Clouds', 70, 'Thunder'],
    'The Diadem': ['Fair Skies', 30, 'Fog', 60, 'Wind', 90, 'Umbral Wind'],
    'Idyllshire': ['Clouds', 10, 'Fog', 20, 'Rain', 30, 'Showers', 40, 'Clear Skies', 70, 'Fair Skies'],
    'The Dravanian Forelands': ['Clouds', 10, 'Fog', 20, 'Thunder', 30, 'Dust Storms', 40, 'Clear Skies', 70, 'Fair Skies'],
    'The Dravanian Hinterlands': ['Clouds', 10, 'Fog', 20, 'Rain', 30, 'Showers', 40, 'Clear Skies', 70, 'Fair Skies'],
    'The Churning Mists': ['Clouds', 10, 'Gales', 20, 'Umbral Static', 40, 'Clear Skies', 70, 'Fair Skies'],
    'Mor Dhona': ['Clouds', 15, 'Fog', 30, 'Gloom', 60, 'Clear Skies', 75, 'Fair Skies'],
    'Rhalgr\'s Reach': ['Clear Skies', 15, 'Fair Skies', 60, 'Clouds', 80, 'Fog', 90, 'Thunder'],
    'The Fringes': ['Clear Skies', 15, 'Fair Skies', 60, 'Clouds', 80, 'Fog', 90, 'Thunder'],
    'The Peaks': ['Clear Skies', 10, 'Fair Skies', 60, 'Clouds', 75, 'Fog', 85, 'Wind', 95, 'Dust Storms'],
    'The Lochs': ['Clear Skies', 20, 'Fair Skies', 60, 'Clouds', 80, 'Fog', 90, 'Thunderstorms'],
    'Kugane': ['Rain', 10, 'Fog', 20, 'Clouds', 40, 'Fair Skies', 80, 'Clear Skies'],
    'Shirogane': ['Rain', 10, 'Fog', 20, 'Clouds', 40, 'Fair Skies', 80, 'Clear Skies'],
    'The Ruby Sea': ['Thunder', 10, 'Wind', 20, 'Clouds', 35, 'Fair Skies', 75, 'Clear Skies'],
    'Yanxia': ['Showers', 5, 'Rain', 15, 'Fog', 25, 'Clouds', 40, 'Fair Skies', 80, 'Clear Skies'],
    'The Azim Steppe': ['Gales', 5, 'Wind', 10, 'Rain', 17, 'Fog', 25, 'Clouds', 35, 'Fair Skies', 75, 'Clear Skies'],
    'Eureka Anemos': ['Fair Skies', 30, 'Gales', 60, 'Showers', 90, 'Snow'],
    'Eureka Pagos': ['Fair Skies', 10, 'Fog', 28, 'Heat Waves', 46, 'Snow', 64, 'Thunder', 82, 'Blizzards'],
    'Eureka Pyros': ['Fair Skies', 10, 'Heat Waves', 28, 'Thunder', 46, 'Blizzards', 64, 'Umbral Wind', 82, 'Snow'],
    'Eureka Hydatos': ['Fair Skies', 12, 'Showers', 34, 'Gloom', 56, 'Thunderstorms', 78, 'Snow'],
    'Bozjan Southern Front': ['Fair Skies', 52, 'Rain', 64, 'Wind', 76, 'Thunder', 88, 'Dust Storms'],
    'Zadnor': ['Fair Skies', 60, 'Rain', 70, 'Wind', 80, 'Thunder', 90, 'Snow'],
    'The Crystarium': ['Clear Skies', 20, 'Fair Skies', 60, 'Clouds', 75, 'Fog', 85, 'Rain', 95, 'Thunderstorms'],
    'Eulmore': ['Gales', 10, 'Rain', 20, 'Fog', 30, 'Clouds', 45, 'Fair Skies', 85, 'Clear Skies'],
    'Lakeland': ['Clear Skies', 20, 'Fair Skies', 60, 'Clouds', 75, 'Fog', 85, 'Rain', 95, 'Thunderstorms'],
    'Kholusia': ['Gales', 10, 'Rain', 20, 'Fog', 30, 'Clouds', 45, 'Fair Skies', 85, 'Clear Skies'],
    'Amh Araeng': ['Fair Skies', 45, 'Clouds', 60, 'Dust Storms', 70, 'Heat Waves', 80, 'Clear Skies'],
    'Il Mheg': ['Rain', 10, 'Fog', 20, 'Clouds', 35, 'Thunderstorms', 45, 'Clear Skies', 60, 'Fair Skies'],
    'The Rak\'tika Greatwood': ['Fog', 10, 'Rain', 20, 'Umbral Wind', 30, 'Clear Skies', 45, 'Fair Skies', 85, 'Clouds'],
    'The Tempest': ['Clouds', 20, 'Fair Skies', 80, 'Clear Skies'],
    'Old Sharlayan': ['Clear Skies', 10, 'Fair Skies', 50, 'Clouds', 70, 'Fog', 85, 'Snow'],
    'Radz-at-Han': ['Fog', 10, 'Rain', 25, 'Clear Skies', 40, 'Fair Skies', 80, 'Clouds'],
    'Labyrinthos': ['Clear Skies', 15, 'Fair Skies', 60, 'Clouds', 85, 'Rain'],
    'Thavnair': ['Fog', 10, 'Rain', 20, 'Showers', 25, 'Clear Skies', 40, 'Fair Skies', 80, 'Clouds'],
    'Garlemald': ['Snow', 45, 'Thunder', 50, 'Rain', 55, 'Fog', 60, 'Clouds', 85, 'Fair Skies', 95, 'Clear Skies'],
    'Mare Lamentorum': ['Umbral Wind', 15, 'Moon Dust', 30, 'Fair Skies'],
    'Elpis': ['Clouds', 25, 'Umbral Wind', 40, 'Fair Skies', 85, 'Clear Skies'],
    'Ultima Thule': ['Astromagnetic Storms', 15, 'Fair Skies', 85, 'Umbral Wind'],
    'Unnamed Island': ['Clear Skies', 25, 'Fair Skies', 70, 'Clouds', 80, 'Rain', 90, 'Fog', 95, 'Showers'],
    'Tuliyollal': ['Clear Skies', 40, 'Fair Skies', 80, 'Clouds', 85, 'Fog', 95, 'Rain'],
    'Urqopacha': ['Clear Skies', 20, 'Fair Skies', 50, 'Clouds', 70, 'Fog', 80, 'Wind', 90, 'Snow'],
    'Kozama\'uka': ['Clear Skies', 25, 'Fair Skies', 60, 'Clouds', 75, 'Fog', 85, 'Rain', 95, 'Showers'],
    'Yak T\'el': ['Clear Skies', 15, 'Fair Skies', 55, 'Clouds', 70, 'Fog', 85, 'Rain'],
    'Solution Nine': ['Fair Skies'],
    'Shaaloani': ['Clear Skies', 5, 'Fair Skies', 50, 'Clouds', 70, 'Dust Storms', 85, 'Gales'],
    'Heritage Found': ['Fair Skies', 5, 'Clouds', 25, 'Fog', 40, 'Rain', 45, 'Thunderstorms', 50, 'Umbral Static'],
    'Living Memory': ['Rain', 10, 'Fog', 20, 'Clouds', 40, 'Fair Skies'],
    'Sinus Ardorum': ['Moon Dust', 15, 'Fair Skies', 85, 'Umbral Wind'],
    'South Horn': ['Clear Skies', 10, 'Fair Skies', 55, 'Clouds', 70, 'Rain', 80, 'Atmospheric Phantasms', 95, 'Illusory Disturbances'],
    'Phaenna': ['Fair Skies', 60, 'Clouds', 80, 'Rain'],
    # ... 추가예정
}

ZONES = list(DATA.keys())

def calculate_forecast_target(timestamp_ms: int) -> int:
    unix = timestamp_ms // 1000
    bell = unix // 175
    increment = (bell + 8 - (bell % 8)) % 24
    total_days = unix // 4200
    calc_base = total_days * 0x64 + increment
    step1 = ((calc_base << 0xB) ^ calc_base) & 0xFFFFFFFF
    step2 = ((step1 >> 8) ^ step1) & 0xFFFFFFFF
    return step2 % 0x64

def get_weather(zone: str):
    target = calculate_forecast_target(int(time() * 1000))
    zone_data = DATA.get(zone)
    if not zone_data:
        return None
    for i in range(0, len(zone_data) - 1, 2):
        weather_name = zone_data[i]
        prob = zone_data[i + 1]
        if target < prob:
            return weather_name
    return zone_data[-1]

def get_weather_at(zone: str, timestamp_ms: int):
    target = calculate_forecast_target(timestamp_ms)
    zone_data = DATA.get(zone)
    if not zone_data:
        return None
    for i in range(0, len(zone_data) - 1, 2):
        weather_name = zone_data[i]
        prob = zone_data[i + 1]
        if target < prob:
            return weather_name
    return zone_data[-1]

def get_weather_icon_filename(en_weather: str) -> str:
    return en_weather.replace(" ", "_") + ".png"


# 날씨창 길이 (지금/다음/다다음 계산용)
WEATHER_WINDOW_MS = 8 * 175 * 1000

WEATHER_KO = {
    "Clear Skies": "쾌청",
    "Fair Skies": "맑음",
    "Clouds": "흐림",
    "Fog": "안개",
    "Rain": "비",
    "Showers": "폭우",
    "Snow": "눈",
    "Blizzards": "눈보라",
    "Thunder": "번개",
    "Thunderstorms": "뇌우",
    "Heat Waves": "작열파",
    "Dust Storms": "모래먼지",
    "Gales": "폭풍",
    "Gloom": "요마의 안개",
    "Umbral Wind": "그림자바람",
    "Umbral Static": "방전",
    "Astromagnetic Storms": "자기 폭풍",
    "Moon Dust": "달모래먼지",
    "Atmospheric Phantasms": "환영",
    "Illusory Disturbances": "환시",
}

ALIAS_KO2EN = {
    "림사 로민사": "Limsa Lominsa",
    "중부 라노시아": "Middle La Noscea",
    "저지 라노시아": "Lower La Noscea",
    "동부 라노시아": "Eastern La Noscea",
    "서부 라노시아": "Western La Noscea",
    "고지 라노시아": "Upper La Noscea",
    "외지 라노시아": "Outer La Noscea",
    "안갯빛 마을": "Mist",

    "그리다니아": "Gridania",
    "검은장막 숲 중부삼림": "Central Shroud",
    "검은장막 숲 동부삼림": "East Shroud",
    "검은장막 숲 남부삼림": "South Shroud",
    "검은장막 숲 북부삼림": "North Shroud",
    "라벤더 안식처": "The Lavender Beds",

    "울다하": "Ul'dah",
    "서부 다날란": "Western Thanalan",
    "중부 다날란": "Central Thanalan",
    "동부 다날란": "Eastern Thanalan",
    "남부 다날란": "Southern Thanalan",
    "북부 다날란": "Northern Thanalan",
    "하늘잔 마루": "The Goblet",

    "이슈가르드": "Ishgard",
    "커르다스 중앙고지": "Coerthas Central Highlands",
    "커르다스 서부고지": "Coerthas Western Highlands",
    "지고천 거리": "Empyreum",

    "아발라시아 구름바다": "The Sea of Clouds",
    "아지스 라": "Azys Lla",
    "디아뎀": "The Diadem",
    "이딜샤이어": "Idyllshire",
    "고지 드라바니아": "The Dravanian Forelands",
    "저지 드라바니아": "The Dravanian Hinterlands",
    "드라바니아 구름바다": "The Churning Mists",

    "모르도나": "Mor Dhona",

    "랄거의 손길": "Rhalgr's Reach",
    "기라바니아 변방지대": "The Fringes",
    "기라바니아 산악지대": "The Peaks",
    "기라바니아 호반지대": "The Lochs",

    "쿠가네": "Kugane",
    "시로가네": "Shirogane",
    "홍옥해": "The Ruby Sea",
    "얀샤": "Yanxia",
    "아짐 대초원": "The Azim Steppe",

    "에우레카 아네모스": "Eureka Anemos",
    "에우레카 파고스": "Eureka Pagos",
    "에우레카 피로스": "Eureka Pyros",
    "에우레카 히다토스": "Eureka Hydatos",

    "남부 보즈야 전선": "Bozjan Southern Front",
    "자트노르 고원": "Zadnor",

    "크리스타리움": "The Crystarium",
    "율모어": "Eulmore",
    "레이크랜드": "Lakeland",
    "콜루시아 섬": "Kholusia",
    "아므 아랭": "Amh Araeng",
    "일 메그": "Il Mheg",
    "라케티카 대삼림": "The Rak'tika Greatwood",
    "템페스트": "The Tempest",

    "올드 샬레이안": "Old Sharlayan",
    "라자한": "Radz-at-Han",
    "라비린토스": "Labyrinthos",
    "사베네어 섬": "Thavnair",
    "갈레말드": "Garlemald",
    "비탄의 바다": "Mare Lamentorum",
    "엘피스": "Elpis",
    "울티마 툴레": "Ultima Thule",
    "이름 없는 섬": "Unnamed Island",

    "툴라이욜라": "Tuliyollal",
    "오르코 파차": "Urqopacha",
    "코자말루 카": "Kozama'uka",
    "야크텔 밀림": "Yak T'el",
    "솔루션 나인": "Solution Nine",
    "샬로니 황야": "Shaaloani",
    "헤리티지 파운드": "Heritage Found",
    "리빙 메모리": "Living Memory",
    "동경의 만": "Sinus Ardorum",
    "초승달 섬 남부": "South Horn",
    "행성 파엔나": "Phaenna",
    # ... 추가예정
}

def norm(s: str) -> str:
    return re.sub(r"[\\s'’`-]", "", s.lower())

def to_korean_zone(zone_key: str) -> str:
    for ko, en in ALIAS_KO2EN.items():
        if en == zone_key:
            return ko
    return zone_key

def to_korean_weather(en_weather: str) -> str:
    return WEATHER_KO.get(en_weather, en_weather)

def find_zone_matches(user_input: str):
    n = norm(user_input)
    # 한글 매치
    ko_matches = [
        en for ko, en in ALIAS_KO2EN.items()
        if n in norm(ko)
    ]
    # 영어 매치
    en_matches = [z for z in ZONES if n in norm(z)]
    all_matches = list(dict.fromkeys(ko_matches + en_matches))  # 중복 제거 & 순서 유지
    all_matches.sort(key=len)
    return all_matches
