from __future__ import annotations

import json
from typing import Any

from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import AzureCliCredential

from app.config import settings

print("FOUNDRY_PROJECT_ENDPOINT:", settings.FOUNDRY_PROJECT_ENDPOINT)
print("FOUNDRY_MODEL:", settings.FOUNDRY_MODEL)


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
                "2. a list of important topics\n"
                "3. exactly 10 structured study questions\n\n"

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

                "For each question, return:\n"
                "- id\n"
                "- topic\n"
                "- question\n"
                "- idealAnswer\n"
                "- keywords\n"
                "- sourceChunkIds\n\n"

                "Return valid JSON only in this exact format:\n"
                "{\n"
                '  "summary": "string",\n'
                '  "topics": ["topic1", "topic2"],\n'
                '  "questions": [\n'
                "    {\n"
                '      "id": "q1",\n'
                '      "topic": "string",\n'
                '      "question": "string",\n'
                '      "idealAnswer": "string",\n'
                '      "keywords": ["string"],\n'
                '      "sourceChunkIds": ["chunk-1"]\n'
                "    }\n"
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
                "topics": [],
                "questions": [],
                "raw_response": "",
            }

        trimmed_text = extracted_text[:12000]

        prompt = (
            "Read the lecture text below and generate a concise exam-focused summary, "
            "important topics, and exactly 10 structured study questions.\n\n"
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
        print("FOUNDRY_MODEL:", settings.FOUNDRY_MODEL)
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
                "topics": [],
                "questions": [],
            }

        summary = parsed.get("summary", "")
        topics = parsed.get("topics", [])
        questions = parsed.get("questions", [])

        if not isinstance(summary, str):
            summary = str(summary)

        if not isinstance(topics, list):
            topics = []

        if not isinstance(questions, list):
            questions = []

        cleaned_questions = []
        for i, q in enumerate(questions[:10], start=1):
            if not isinstance(q, dict):
                continue

            cleaned_questions.append({
                "id": str(q.get("id", f"q{i}")),
                "topic": str(q.get("topic", "")),
                "question": str(q.get("question", "")).strip(),
                "idealAnswer": str(q.get("idealAnswer", "")).strip(),
                "keywords": [str(k).strip() for k in q.get("keywords", []) if str(k).strip()],
                "sourceChunkIds": [str(cid).strip() for cid in q.get("sourceChunkIds", []) if str(cid).strip()],
            })

        return {
            "summary": summary,
            "topics": [str(t).strip() for t in topics if str(t).strip()],
            "questions": cleaned_questions,
            "raw_response": raw_text,
        }

    async def close(self) -> None:
        await self.credential.close()