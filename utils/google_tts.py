import os
import uuid
from google.cloud import texttospeech
from utils.tts_engine import preprocess

client = texttospeech.TextToSpeechClient()

LANG = "ko-KR"

VOICE_MAP = {
    "female_a": "ko-KR-Standard-A",
    "female_b": "ko-KR-Standard-B",
    "male_a": "ko-KR-Standard-C",
    "male_b": "ko-KR-Standard-D",
}

def google_tts(text: str, style="female_a"):
    text = preprocess(text)
    voice_name = VOICE_MAP.get(style, VOICE_MAP["female_a"])

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice_params = texttospeech.VoiceSelectionParams(
        language_code=LANG,
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config
    )

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join("voice", filename)
    os.makedirs("voice", exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(response.audio_content)
    return filepath
