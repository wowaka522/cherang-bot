import subprocess
import uuid
import os
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16
)

voice = texttospeech.VoiceSelectionParams(
    language_code="ko-KR",
    name="ko-KR-Neural2-A"  # 자연스러운 여성 음성
)

# 🗣️ Google TTS → ffmpeg 변환 → Discord OGG 파일 출력
def google_tts(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # 임시 wav 파일 & ogg 파일 이름
    tmp_id = uuid.uuid4().hex
    wav_path = f"/tmp/{tmp_id}.wav"
    ogg_path = f"/tmp/{tmp_id}.ogg"

    # WAV 저장
    with open(wav_path, "wb") as f:
        f.write(response.audio_content)

    # 🔄 ffmpeg: wav → ogg (discord 호환)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", wav_path,
        "-acodec", "libopus",
        "-ar", "48000",
        "-ac", "2",
        ogg_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 변환 후 wav 삭제 (깨끗🎯)
    os.remove(wav_path)

    # Discord에서 바로 재생 가능한 ogg 파일 경로 반환
    return ogg_path
