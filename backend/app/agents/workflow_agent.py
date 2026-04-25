from __future__ import annotations

import json
from typing import Any

from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import AzureCliCredential

from app.config import settings


class WorkflowAgent:
    def __init__(self) -> None:
        self.credential = AzureCliCredential()

        self.client = FoundryChatClient(
            credential=self.credential,
            project_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
            model=settings.FOUNDRY_MODEL,
        )

        self.agent = self.client.as_agent(
            name="WorkflowAgent",
            instructions=(
                "You are WorkflowAgent, the study session manager.\n"
                "You receive:\n"
                "- current question\n"
                "- coach evaluation result\n"
                "- session state\n\n"
                "Your job is to decide the next action in the study session.\n\n"
                "Preferred rules:\n"
                "- If score >= 0.8, return action 'advance'\n"
                "- Else if score >= 0.5 and retry count is 0, return action 'hint_retry'\n"
                "- Else return action 'reveal_and_move'\n\n"
                "If the question already contains a hint, use it.\n"
                "If no hint exists, derive a short simple hint from missing concepts, keywords, or ideal answer.\n\n"
                "Return valid JSON only in this exact format:\n"
                "{\n"
                '  "action": "advance",\n'
                '  "questionId": "q1",\n'
                '  "messageToUser": "Good job. Let\'\s move to the next question.",\n'
                '  "retryAllowed": false\n'
                "}"
            ),
        )

        self.state = {
            "currentQuestionIndex": 0,
            "retryCountByQuestion": {},
            "weakTopics": [],
            "history": [],
        }

    def get_state(self) -> dict[str, Any]:
        return self.state

    def init_question(self, question_id: str) -> None:
        if question_id not in self.state["retryCountByQuestion"]:
            self.state["retryCountByQuestion"][question_id] = 0

    def derive_fallback_hint(
        self,
        question: dict[str, Any],
        coach_result: dict[str, Any],
    ) -> str:
        if question.get("hint"):
            return str(question["hint"])

        missing = coach_result.get("missingConcepts", [])
        if isinstance(missing, list) and missing:
            return f"You are close. Think about these missing ideas: {', '.join(missing[:3])}."

        keywords = question.get("keywords", [])
        if isinstance(keywords, list) and keywords:
            return f"Focus on these key ideas: {', '.join(keywords[:3])}."

        ideal = str(question.get("idealAnswer", "")).strip()
        if ideal:
            short = ideal[:160].strip()
            return f"Think about this core idea: {short}"

        return "Try again by explaining the main concept more completely."

    def apply_state_update(
        self,
        question: dict[str, Any],
        coach_result: dict[str, Any],
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        question_id = question["id"]
        topic = question.get("topic", "")
        score = float(coach_result.get("score", 0.0))
        recommendation = str(coach_result.get("recommendation", decision.get("action", "reveal_and_move")))

        self.init_question(question_id)

        self.state["history"].append({
            "questionId": question_id,
            "score": score,
            "recommendation": recommendation,
        })

        action = decision.get("action", "reveal_and_move")

        if action == "hint_retry":
            self.state["retryCountByQuestion"][question_id] = self.state["retryCountByQuestion"].get(question_id, 0) + 1
        else:
            self.state["currentQuestionIndex"] += 1

        if action == "reveal_and_move" and topic:
            if topic not in self.state["weakTopics"]:
                self.state["weakTopics"].append(topic)

        return decision

    def fallback_decision(
        self,
        question: dict[str, Any],
        coach_result: dict[str, Any],
    ) -> dict[str, Any]:
        question_id = question["id"]
        score = float(coach_result.get("score", 0.0))
        retry_count = self.state["retryCountByQuestion"].get(question_id, 0)

        if score >= 0.8:
            return {
                "action": "advance",
                "questionId": question_id,
                "messageToUser": "Good job. Let’s move to the next question.",
                "retryAllowed": False,
            }

        if score >= 0.5 and retry_count == 0:
            hint = self.derive_fallback_hint(question, coach_result)
            return {
                "action": "hint_retry",
                "questionId": question_id,
                "messageToUser": hint,
                "retryAllowed": True,
            }

        return {
            "action": "reveal_and_move",
            "questionId": question_id,
            "messageToUser": f"The ideal answer is: {question.get('idealAnswer', '')} Let’s move to the next question.",
            "retryAllowed": False,
        }

    async def decide_next_action(
        self,
        question: dict[str, Any],
        coach_result: dict[str, Any],
    ) -> dict[str, Any]:
        question_id = question["id"]
        self.init_question(question_id)

        payload = {
            "question": question,
            "coachResult": coach_result,
            "sessionState": self.state,
        }

        prompt = (
            "Decide the next study-session action and return valid JSON only.\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

        print("Calling WorkflowAgent...")
        print("Question ID:", question_id)
        print("Current retry count:", self.state["retryCountByQuestion"].get(question_id, 0))

        try:
            response = await self.agent.run(prompt)
            raw_text = str(response).strip()

            print("WorkflowAgent raw response:")
            print(raw_text[:2000])

            parsed = json.loads(raw_text)

            action = str(parsed.get("action", "reveal_and_move"))
            if action not in {"advance", "hint_retry", "reveal_and_move"}:
                raise ValueError("Invalid action returned")

            decision = {
                "action": action,
                "questionId": str(parsed.get("questionId", question_id)),
                "messageToUser": str(parsed.get("messageToUser", "")),
                "retryAllowed": bool(parsed.get("retryAllowed", action == "hint_retry")),
            }

            if action == "hint_retry" and not decision["messageToUser"]:
                decision["messageToUser"] = self.derive_fallback_hint(question, coach_result)

        except Exception as e:
            print("WorkflowAgent fallback triggered:", e)
            decision = self.fallback_decision(question, coach_result)

        return self.apply_state_update(question, coach_result, decision)

    async def close(self) -> None:
        await self.credential.close()