import uuid
import numpy as np
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

def google_tts(text: str):
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="ko-KR",
        name="ko-KR-WooJinNeural"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=24000
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # 바이트 → numpy 변환
    import soundfile as sf
    import io
    buffer = io.BytesIO(response.audio_content)
    audio, sr = sf.read(buffer)
    return audio.astype(np.float32)
