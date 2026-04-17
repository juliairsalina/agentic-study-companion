from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.storage_service import save_uploaded_file
from app.services.pdf_service import extract_text_from_pdf

router = APIRouter(prefix="/upload", tags=["upload"])


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

        if extracted_text.strip():
            print("=== EXTRACTED TEXT PREVIEW START ===")
            print(extracted_text[:2000])
            print("=== EXTRACTED TEXT PREVIEW END ===")
        else:
            print("No readable text extracted from this PDF.")

    except Exception as e:
        print(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")

    preview_text = extracted_text[:1500] if extracted_text else ""

    print("=== UPLOAD END ===\n")

    return {
        "message": "PDF uploaded and extracted successfully",
        "filename": pdf.filename,
        "instruction": instruction,
        "saved_path": saved_path,
        "text_preview": preview_text,
        "extracted_text": extracted_text,
        "text_length": len(extracted_text)
    }