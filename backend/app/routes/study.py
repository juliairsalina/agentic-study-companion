from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.speech_service import transcribe_audio_file
from app.database import list_study_sessions, get_study_session

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


@router.get("/sessions")
async def get_saved_sessions():
    """
    Used by frontend old flashcards section.
    """
    try:
        sessions = list_study_sessions(user_id="demo-user")
        return {
            "sessions": sessions
        }
    except Exception as e:
        print(f"Failed to load study sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load study sessions: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_saved_session(session_id: str):
    """
    Used when user opens one old flashcard session.
    """
    try:
        session = get_study_session(
            session_id=session_id,
            user_id="demo-user",
        )
        return session
    except Exception as e:
        print(f"Failed to load study session: {e}")
        raise HTTPException(status_code=404, detail=str(e))