from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.agents.workflow_agent import WorkflowAgent

router = APIRouter(prefix="/workflow", tags=["workflow"])

workflow_agent = WorkflowAgent()


class WorkflowRequest(BaseModel):
    question: dict[str, Any]
    coachResult: dict[str, Any]


@router.post("/decide")
async def decide_next_action(payload: WorkflowRequest):
    try:
        result = await workflow_agent.decide_next_action(
            question=payload.question,
            coach_result=payload.coachResult,
        )
        return {
            "decision": result,
            "state": workflow_agent.get_state(),
        }
    except Exception as e:
        print(f"WorkflowAgent failed: {e}")
        raise HTTPException(status_code=500, detail=f"WorkflowAgent failed: {str(e)}")