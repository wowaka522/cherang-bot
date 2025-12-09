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
    name="ko-KR-Neural2-A"
)

def google_tts(text: str) -> str:
    synthesis_input = texttospeech.SynthesisInput(text=text)
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    tmp_id = uuid.uuid4().hex
    wav_path = f"/tmp/{tmp_id}.wav"
    ogg_path = f"/tmp/{tmp_id}.ogg"

    with open(wav_path, "wb") as f:
        f.write(response.audio_content)

    # ffmpeg: wav → opus (Discord 호환)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", wav_path,
        "-acodec", "libopus",
        ogg_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.remove(wav_path)
    return ogg_path
