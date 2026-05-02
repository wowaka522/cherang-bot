# utils/text_cleaner.py
from __future__ import annotations

import re


# 채팅에서 아이템/지역 뽑을 때 쓰는 “가벼운” 정리 유틸
# (너 프로젝트 구조상, 여기서 더 고도화해도 되고 Step2에서 services로 옮겨도 됨)

_ws = re.compile(r"\s+")

# ✅ 자연어 트리거(입력 파싱 규칙): 코드에 유지
_weather_suffix = re.compile(r"\s*(?:날씨|기상|어때)\s*$")


def _clean(s: str) -> str:
    s = (s or "").strip()
    s = _ws.sub(" ", s)
    return s


def extract_item_name(text: str) -> str:
    """
    /시세 슬래시 입력, 또는 자연어 메시지에서 '아이템 이름'만 최대한 뽑아내는 용도.
    지금은 최소 기능만: 앞뒤 공백 정리.
    """
    return _clean(text)


def extract_city_name(text: str) -> str:
    """
    자연어에서 '지역 키워드'만 뽑는 용도.
    - 끝에 붙는 날씨 트리거(날씨/기상/어때)를 제거
    - 공백 정리
    """
    s = _clean(text)
    s = _weather_suffix.sub("", s).strip()
    return _clean(s)