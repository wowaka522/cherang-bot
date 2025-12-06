# utils/text_cleaner.py
import re

# 체랑봇 호출 단어
CALL_WORDS = [
    "체랑", "체랑아", "체랑봇",
    "냥이", "냥이야", "냥아"
]

# 시세 관련 키워드
PRICE_WORDS = ["시세", "얼마", "가격", "비싸", "값"]

# 날씨 관련 키워드
WEATHER_WORDS = ["날씨", "기상", "어때"]


def clean_text_for_search(content: str):
    """기본 전처리 + 호출어 제거 + 문장 앞 '야', '아' 제거"""
    text = re.sub(r"[^0-9A-Za-zㄱ-힣 ]+", " ", content)
    text = text.strip()

    # 호출어 제거
    for w in CALL_WORDS:
        text = text.replace(w, "")

    # 문장 맨 앞에 '야', '아' 남았을 때 제거
    if text.startswith("야") or text.startswith("아"):
        text = text[1:].strip()

    return text


def extract_item_name(content: str):
    """자연어 -> 아이템 이름만 뽑아냄"""
    text = clean_text_for_search(content)

    for w in PRICE_WORDS:
        text = text.replace(w, "")

    text = text.replace("알려줘", "").replace("봐줘", "")

    return text.strip()


def extract_city_name(content: str):
    """자연어 -> 지역 이름만 뽑아냄"""
    text = clean_text_for_search(content)

    for w in WEATHER_WORDS:
        text = text.replace(w, "")

    text = text.replace("알려줘", "").replace("봐줘", "")

    return text.strip()