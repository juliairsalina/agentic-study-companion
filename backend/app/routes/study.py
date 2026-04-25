from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.speech_service import transcribe_audio_file

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    try:
        result = transcribe_audio_file(audio_bytes, file_suffix=".webm")
        return result
    except Exception as e:
        print(f"Speech transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Speech transcription failed: {str(e)}")