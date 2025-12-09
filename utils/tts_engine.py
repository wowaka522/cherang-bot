import subprocess
import uuid
import os
from pathlib import Path
from google.cloud import texttospeech
import requests
import re

TEMP_PATH = Path("voice/temp")
TEMP_PATH.mkdir(parents=True, exist_ok=True)

client = texttospeech.TextToSpeechClient()
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16
)

TTS_URL_TEMPLATE = "https://speech.platform.bing.com/synthesize?speaker={voice}&lang=ko-KR"

_initial_swears = {
    "ㅅㅂ": "씨발",
    "ㅂㅅ": "병신",
    "ㅈㄴ": "존나",
    "ㅈ같": "좆같",
    "ㄱㅅㄲ": "개새끼",
    "ㄴㅇㅁ": "느금마",
    "ㅁㅊ": "미친"
}

def preprocess(text):
    url_pattern = r"(https?://\S+|discord\.gg/\S+|www\.\S+)"
    if re.search(url_pattern, text, re.IGNORECASE):
        return "링크가 도착했어요."

    for k, v in _initial_swears.items():
        text = text.replace(k, v)

    return text


def google_tts(text: str, voice_name: str):
    tmp_id = uuid.uuid4().hex
    wav_path = f"/tmp/{tmp_id}.wav"
    ogg_path = f"/tmp/{tmp_id}.ogg"

    voice = texttospeech.VoiceSelectionParams(
        language_code="ko-KR",
        name=voice_name,
    )

    synth_input = texttospeech.SynthesisInput(text=text)
    res = client.synthesize_speech(
        input=synth_input,
        voice=voice,
        audio_config=audio_config
    )

    with open(wav_path, "wb") as f:
        f.write(res.audio_content)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", wav_path,
        "-acodec", "libopus",
        ogg_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.remove(wav_path)
    return ogg_path


def bing_tts(text: str, voice_name: str):
    tmp_id = uuid.uuid4().hex
    wav_path = TEMP_PATH / f"{tmp_id}.wav"
    ogg_path = TEMP_PATH / f"{tmp_id}.ogg"
    
    url = TTS_URL_TEMPLATE.format(voice=voice_name)

    res = requests.post(url, data=text.encode("utf-8"))
    if res.status_code != 200 or not res.content:
        print("[TTS] Bing Error", res.status_code)
        return None

    wav_path.write_bytes(res.content)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(wav_path),
        "-acodec", "libopus",
        str(ogg_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.remove(wav_path)
    return str(ogg_path)
