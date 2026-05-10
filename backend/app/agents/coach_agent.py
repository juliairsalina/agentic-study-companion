from __future__ import annotations

import json
from typing import Any

from agent_framework.foundry import FoundryChatClient
import os
from azure.identity.aio import AzureCliCredential, ManagedIdentityCredential

from app.config import settings


class CoachAgent:
    def __init__(self) -> None:
        if os.getenv("WEBSITE_SITE_NAME"):
            print("CoachAgent auth: using ManagedIdentityCredential")
            self.credential = ManagedIdentityCredential()
        else:
            print("CoachAgent auth: using AzureCliCredential for local development")
            self.credential = AzureCliCredential()

        self.client = FoundryChatClient(
            credential=self.credential,
            project_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
            model=settings.FOUNDRY_MODEL,
        )

        self.agent = self.client.as_agent(
            name="CoachAgent",
            instructions=(
                "You are CoachAgent, an answer evaluation assistant for spoken study answers.\n"
                "You receive:\n"
                "- questionId\n"
                "- topic\n"
                "- question\n"
                "- transcript\n"
                "- idealAnswer\n"
                "- keywords\n"
                "- sourceChunkIds\n\n"
                "Your job is to evaluate concept coverage.\n\n"
                "Scoring guidance:\n"
                "- 0.8 to 1.0: mostly correct and complete\n"
                "- 0.5 to 0.79: partially correct, but missing important concepts\n"
                "- below 0.5: weak or incorrect answer\n\n"
                "Recommendation rules:\n"
                "- use 'advance' if the answer is strong enough\n"
                "- use 'hint_retry' if the answer is partially correct\n"
                "- use 'reveal_and_move' if the answer is weak\n\n"
                
                "Return valid JSON only in this exact format:\n"
                "{\n"
                '  "questionId": "q1",\n'
                '  "score": 0.72,\n'
                '  "matchedKeywords": ["keyword1"],\n'
                '  "missingConcepts": ["concept1"],\n'
                '  "feedback": "string",\n'
                '  "recommendation": "hint_retry"\n'
                "}"
            ),
        )

    async def evaluate_answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Evaluate this spoken-answer attempt and return valid JSON only.\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

        print("Calling CoachAgent...")
        print("Question ID:", payload.get("questionId"))
        print("Transcript:", payload.get("transcript", "")[:300])

        response = await self.agent.run(prompt)
        raw_text = str(response).strip()

        print("CoachAgent raw response:")
        print(raw_text[:2000])

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            parsed = {
                "questionId": payload.get("questionId", ""),
                "score": 0.0,
                "matchedKeywords": [],
                "missingConcepts": payload.get("keywords", []),
                "feedback": raw_text,
                "recommendation": "reveal_and_move",
            }

        question_id = str(parsed.get("questionId", payload.get("questionId", "")))
        score = parsed.get("score", 0.0)
        matched_keywords = parsed.get("matchedKeywords", [])
        missing_concepts = parsed.get("missingConcepts", [])
        feedback = str(parsed.get("feedback", ""))
        recommendation = str(parsed.get("recommendation", "reveal_and_move"))

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0

        if not isinstance(matched_keywords, list):
            matched_keywords = []

        if not isinstance(missing_concepts, list):
            missing_concepts = []

        if recommendation not in {"advance", "hint_retry", "reveal_and_move"}:
            recommendation = "reveal_and_move"

        return {
            "questionId": question_id,
            "score": score,
            "matchedKeywords": [str(x).strip() for x in matched_keywords if str(x).strip()],
            "missingConcepts": [str(x).strip() for x in missing_concepts if str(x).strip()],
            "feedback": feedback,
            "recommendation": recommendation,
            "raw_response": raw_text,
        }

    async def close(self) -> None:
        await self.credential.close()