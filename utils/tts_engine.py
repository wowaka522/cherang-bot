import uuid
from pathlib import Path
import requests

VOICE_PATH = Path("voice")
TEMP_PATH = VOICE_PATH / "temp"
TEMP_PATH.mkdir(parents=True, exist_ok=True)

# 한국어 음성
VOICE_NAME = "SunHiNeural"  # 여성
# VOICE_NAME = "BongJinNeural"  # 남성 (원하면 변경)

TTS_URL = f"https://speech.platform.bing.com/synthesize?speaker={VOICE_NAME}&lang=ko-KR"


def normalize_text(text: str) -> str:
    return text.strip()[:200]


async def synth_to_file(text: str) -> Path:
    filename = f"{uuid.uuid4().hex}.wav"
    out = TEMP_PATH / filename

    print(f"[TTS] 생성 시도 → {filename}")

    try:
        res = requests.post(TTS_URL, data=text.encode("utf-8"))
        if res.status_code == 200 and res.content:
            out.write_bytes(res.content)
            print(f"[TTS 완료] {out}")
            return out

        print(f"[TTS ERROR] status={res.status_code}, size={len(res.content)}")
        return None

    except Exception as e:
        print("[TTS ERROR]", e)
        return None
