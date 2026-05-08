import os
import tempfile
import threading
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

        done = threading.Event()
        transcripts: list[str] = []
        error_holder: list[str] = []

        def recognized_handler(event):
            if event.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = event.result.text.strip()
                if text:
                    print(f"Recognized: {text}")
                    transcripts.append(text)

            elif event.result.reason == speechsdk.ResultReason.NoMatch:
                print("No speech could be recognized for this segment.")

        def canceled_handler(event):
            cancellation = event.result.cancellation_details

            print(
                f"Speech recognition canceled: "
                f"{cancellation.reason} - {cancellation.error_details}"
            )

            # EndOfStream simply means Azure finished reading the uploaded audio file.
            # For file-based transcription, this is expected and should not be treated as an error.
            if cancellation.reason == speechsdk.CancellationReason.EndOfStream:
                done.set()
                return

            error_message = (
                f"Speech recognition canceled: "
                f"{cancellation.reason} - {cancellation.error_details}"
            )

            error_holder.append(error_message)
            done.set()

        def session_stopped_handler(event):
            print("Speech recognition session stopped.")
            done.set()

        recognizer.recognized.connect(recognized_handler)
        recognizer.canceled.connect(canceled_handler)
        recognizer.session_stopped.connect(session_stopped_handler)

        recognizer.start_continuous_recognition()

        # Wait until Azure finishes reading the uploaded audio file.
        done.wait(timeout=120)

        recognizer.stop_continuous_recognition()

        if error_holder:
            raise RuntimeError(error_holder[0])

        final_transcript = " ".join(transcripts).strip()

        return {
            "transcript": final_transcript,
            "confidence": None,
            "raw": {
                "segments": transcripts,
                "segment_count": len(transcripts),
            },
        }

    finally:
        try:
            os.remove(temp_audio_path)
        except OSError:
            pass