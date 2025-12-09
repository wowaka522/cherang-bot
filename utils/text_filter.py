import re

def preprocess_tts_text(text: str) -> str:
    # 1️⃣ URL 감지
    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, text):
        return "링크가 도착했어요."

    # 2️⃣ 초성 욕 치환
    bad_word_map = {
        "ㅅㅂ": "씨발",
        "ㅈㄴ": "존나",
        "ㅂㅅ": "병신",
        "ㅗ": "욕을 하고 있어요",
        "ㄲㅈ": "꺼져",
    }

    for k, v in bad_word_map.items():
        text = text.replace(k, v)

    return text
