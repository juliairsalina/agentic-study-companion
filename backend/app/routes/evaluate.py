from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.coach_agent import CoachAgent

router = APIRouter(prefix="/evaluate", tags=["evaluate"])

coach_agent = CoachAgent()


class EvaluateRequest(BaseModel):
    questionId: str
    topic: str
    question: str
    transcript: str
    idealAnswer: str
    keywords: list[str]
    sourceChunkIds: list[str] = []


@router.post("/")
async def evaluate_answer(payload: EvaluateRequest):
    if not payload.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is empty.")

    try:
        result = await coach_agent.evaluate_answer(payload.model_dump())
        return result
    except Exception as e:
        print(f"CoachAgent failed: {e}")
        raise HTTPException(status_code=500, detail=f"CoachAgent failed: {str(e)}")