import os
import tempfile
from typing import Any

import azure.cognitiveservices.speech as speechsdk

from app.config import settings


def transcribe_audio_file(audio_bytes: bytes, file_suffix: str = ".wav") -> dict[str, Any]:
    if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
        raise RuntimeError("Azure Speech credentials are missing.")

    speech_config = speechsdk.SpeechConfig(
        subscription=settings.AZURE_SPEECH_KEY,
        region=settings.AZURE_SPEECH_REGION,
    )
    speech_config.speech_recognition_language = "en-US"

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    try:
        audio_config = speechsdk.audio.AudioConfig(filename=temp_audio_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        result = recognizer.start_continuous_recognition()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            json_result = result.properties.get(
                speechsdk.PropertyId.SpeechServiceResponse_JsonResult
            )

            return {
                "transcript": result.text,
                "confidence": None,
                "raw": json_result,
            }

        if result.reason == speechsdk.ResultReason.NoMatch:
            return {
                "transcript": "",
                "confidence": None,
                "raw": "No speech could be recognized.",
            }

        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            raise RuntimeError(
                f"Speech recognition canceled: {cancellation.reason} - {cancellation.error_details}"
            )

        return {
            "transcript": "",
            "confidence": None,
            "raw": "Unknown speech recognition result.",
        }

    finally:
        try:
            os.remove(temp_audio_path)
        except OSError:
            pass