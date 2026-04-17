from __future__ import annotations

import json
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import AzureCliCredential

from app.config import settings


class ContentAgent:
    def __init__(self) -> None:
        self.credential = AzureCliCredential()

        self.client = FoundryChatClient(
            credential=self.credential,
            project_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
            model=settings.FOUNDRY_MODEL,
        )

        self.agent = self.client.as_agent(
            name="ContentAgent",
            instructions=(
                "You are ContentAgent, an AI study assistant for lecture PDFs. "
                "Read extracted lecture text and return:\n"
                "1. a concise exam-focused summary\n"
                "2. exactly 10 study questions\n\n"

                "Prioritize these in order:\n"
                "1. Hot-topic concepts that are central, repeated, or emphasized\n"
                "2. Definitions and key terms\n"
                "3. Comparisons and differences between related concepts\n"
                "4. Processes, workflows, mechanisms, or ordered steps\n"
                "5. Important emphasized content such as headings, repeated phrases, or title-like content\n\n"

                "Question-writing rules:\n"
                "- Generate exactly 10 questions.\n"
                "- Make them useful for active recall.\n"
                "- Prefer short, clear, exam-style questions.\n"
                "- Avoid vague or overly broad questions.\n"
                "- Avoid duplicate questions.\n"
                "- Base every question only on the provided lecture text.\n"
                "- Do not invent facts or use outside knowledge.\n\n"

                "Summary-writing rules:\n"
                "- Write a concise summary for a student preparing for an exam.\n"
                "- Focus on major concepts, definitions, comparisons, and processes.\n"
                "- Do not add filler.\n\n"

                "Return valid JSON only in this exact format:\n"
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
            ),
        )

    async def summarize_and_generate_questions(
        self,
        extracted_text: str,
        study_instruction: str = "",
    ) -> dict[str, Any]:
        if not extracted_text or not extracted_text.strip():
            return {
                "summary": "No readable text was extracted from the PDF.",
                "questions": [],
                "raw_response": "",
            }

        trimmed_text = extracted_text[:12000]

        prompt = (
            "Read the lecture text below and generate a concise exam-focused summary "
            "and exactly 10 study questions.\n\n"
            f"Optional user instruction: {study_instruction or 'None'}\n\n"
            "Focus especially on:\n"
            "- hot topics\n"
            "- definitions\n"
            "- comparisons\n"
            "- processes or ordered steps\n"
            "- emphasized or repeated concepts\n\n"
            "Lecture text:\n"
            f"{trimmed_text}\n\n"
            "Return valid JSON only."
        )

        print("Creating ContentAgent request...")
        print("Foundry model:", settings.FOUNDRY_MODEL)
        print("Extracted text length:", len(extracted_text))
        print("Trimmed text length:", len(trimmed_text))

        response = await self.agent.run(prompt)
        raw_text = str(response).strip()

        print("ContentAgent raw response:")
        print(raw_text[:2000])

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
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

        questions = [str(q).strip() for q in questions if str(q).strip()]
        questions = questions[:10]

        return {
            "summary": summary,
            "questions": questions,
            "raw_response": raw_text,
        }

    async def close(self) -> None:
        await self.credential.close()