from __future__ import annotations

import json
from typing import Any, Dict, List

from agent_framework.azure import AzureOpenAIChatClient

from app.config import settings


class ContentAgent:
    def __init__(self) -> None:
        self.client = AzureOpenAIChatClient(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT,
            api_key=settings.AZURE_OPENAI_API_KEY,
        )

        self.agent = self.client.create_agent(
            name="ContentAgent",
            instructions=(
            "You are ContentAgent, an AI study assistant for lecture PDFs. "
            "Your job is to read extracted lecture text and generate:\n"
            "1. a concise student-friendly summary\n"
            "2. exactly 10 study questions\n\n"

            "Your questions must focus on the most exam-relevant content. "
            "Prioritize these types of content in this order:\n"
            "1. Hot-topic concepts that seem central or repeatedly emphasized\n"
            "2. Definitions and key terms\n"
            "3. Comparisons and differences between related concepts\n"
            "4. Processes, workflows, mechanisms, or ordered steps\n"
            "5. Important emphasized content such as bold-looking headings, repeated phrases, highlighted ideas, or section titles\n\n"

            "Question-writing rules:\n"
            "- Generate exactly 10 questions.\n"
            "- Make the questions useful for active recall study.\n"
            "- Prefer short, clear, exam-style questions.\n"
            "- Avoid vague or overly broad questions.\n"
            "- Avoid duplicate questions.\n"
            "- If there are not enough strong topics, still produce 10 questions using the most important available content.\n"
            "- Base every question only on the provided lecture text.\n"
            "- Do not invent facts or add outside knowledge.\n\n"

            "Summary-writing rules:\n"
            "- Write a concise summary for a student preparing for an exam.\n"
            "- Focus on major concepts, definitions, comparisons, and processes.\n"
            "- Do not include unnecessary filler.\n\n"

            "Return valid JSON only.\n"
            "Use this exact format:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "questions": [\n'
            '    "question 1",\n'
            '    "question 2",\n'
            '    "question 3",\n'
            '    "question 4",\n'
            '    "question 5",\n'
            '    "question 6",\n'
            '    "question 7",\n'
            '    "question 8",\n'
            '    "question 9",\n'
            '    "question 10"\n'
            "  ]\n"
            "}"
                "}"
            ),
            temperature=0.3,
        )

    async def summarize_and_generate_questions(
        self,
        extracted_text: str,
        study_instruction: str = "",
    ) -> Dict[str, Any]:
        if not extracted_text or not extracted_text.strip():
            return {
                "summary": "No readable text was extracted from the PDF.",
                "questions": [],
            }

        prompt = (
            "Read the lecture text below and generate a concise exam-focused summary and exactly 10 study questions.\n\n"
            f"Optional user instruction: {study_instruction or 'None'}\n\n"
            "Focus especially on:\n"
            "- hot topics\n"
            "- definitions\n"
            "- comparisons\n"
            "- processes or ordered steps\n"
            "- emphasized or repeated concepts\n\n"
            "Lecture text:\n"
            f"{extracted_text}\n\n"
            "Return valid JSON only."
        )

        result = await self.agent.run(prompt)

        # Agent Framework examples show `agent.run(...)` returning the model result.
        # We coerce it to string and parse JSON.
        raw_text = str(result).strip()

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            # Safe fallback if model output is not perfect JSON
            parsed = {
                "summary": raw_text,
                "questions": [],
            }

        summary = parsed.get("summary", "")
        questions = parsed.get("questions", [])

        if not isinstance(summary, str):
            summary = str(summary)

        if not isinstance(questions, list):
            questions = []

        # Keep only string questions
        questions = [str(q).strip() for q in questions if str(q).strip()]

        return {
            "summary": summary,
            "questions": questions,
            "raw_response": raw_text,
        }