import os
import azure.cognitiveservices.speech as speechsdk

def azure_tts(text: str, voice="ko-KR-WooJinNeural"):
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_REGION")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=region)
    speech_config.speech_synthesis_voice_name = voice

    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False)

    speech = speechsdk.SpeechSynthesizer(speech_config, audio_config)

    result = speech.speak_text_async(text).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError(result.reason)

    return result.audio_data
