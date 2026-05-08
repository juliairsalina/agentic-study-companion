from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.storage_service import save_uploaded_file
from app.services.pdf_service import extract_text_from_pdf
from app.agents.content_agent import ContentAgent
from app.database import create_study_session

router = APIRouter(prefix="/upload", tags=["upload"])

content_agent = ContentAgent()


@router.post("/")
async def upload_pdf(
    pdf: UploadFile = File(...),
    instruction: str = Form(default="")
):
    if not pdf.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    if not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    print("\n=== UPLOAD START ===")
    print(f"Filename: {pdf.filename}")
    print(f"Instruction: {instruction}")

    saved_path = save_uploaded_file(pdf)
    print(f"Saved path: {saved_path}")

    try:
        print("Starting PDF extraction...")
        extracted_text = extract_text_from_pdf(saved_path)
        print("Extraction finished.")
        print(f"Extracted text length: {len(extracted_text)}")
    except Exception as e:
        print(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")

    if not extracted_text.strip():
        print("No readable text extracted from this PDF.")
        return {
            "message": "PDF uploaded but no readable text was extracted",
            "filename": pdf.filename,
            "instruction": instruction,
            "saved_path": saved_path,
            "text_preview": "",
            "extracted_text": "",
            "text_length": 0,
            "summary": "No readable text could be extracted from this PDF.",
            "topics": [],
            "questions": [],
            "sessionId": None,
        }

    try:
        print("Calling ContentAgent...")
        agent_result = await content_agent.summarize_and_generate_questions(
            extracted_text=extracted_text,
            study_instruction=instruction,
        )
        print("ContentAgent finished.")
        print("Generated question count:", len(agent_result["questions"]))
    except Exception as e:
        print(f"ContentAgent failed: {e}")
        raise HTTPException(status_code=500, detail=f"ContentAgent failed: {str(e)}")

    summary = agent_result.get("summary", "")
    topics = agent_result.get("topics", [])
    questions = agent_result.get("questions", [])

    try:
        print("Saving study session to Cosmos DB...")
        session_doc = create_study_session(
            filename=pdf.filename,
            instruction=instruction,
            saved_path=saved_path,
            extracted_text=extracted_text,
            summary=summary,
            topics=topics,
            questions=questions,
            user_id="demo-user",
        )
        print(f"Saved session ID: {session_doc['id']}")
    except Exception as e:
        print(f"Cosmos DB save failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cosmos DB save failed: {str(e)}")

    print("=== UPLOAD END ===\n")

    return {
        "message": "PDF uploaded and processed successfully",
        "sessionId": session_doc["id"],
        "filename": pdf.filename,
        "instruction": instruction,
        "saved_path": saved_path,
        "text_preview": extracted_text[:1500],
        "extracted_text": extracted_text,
        "text_length": len(extracted_text),
        "summary": summary,
        "topics": topics,
        "questions": questions,
    }