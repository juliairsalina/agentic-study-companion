from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.storage_service import save_uploaded_file

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

    saved_path = save_uploaded_file(pdf)

    return {
        "message": "PDF uploaded successfully",
        "filename": pdf.filename,
        "instruction": instruction,
        "saved_path": saved_path
    }