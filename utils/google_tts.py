voice_name = "ko-KR-Neural2-B"
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
    speaking_rate=1.0
)

input_text = texttospeech.SynthesisInput(text=text)

voice_params = texttospeech.VoiceSelectionParams(
    language_code="ko-KR",
    name=voice_name
)

response = client.synthesize_speech(
    request={"input": input_text, "voice": voice_params, "audio_config": audio_config}
)
audio_data, _ = sf.read(io.BytesIO(response.audio_content), dtype="int16")
