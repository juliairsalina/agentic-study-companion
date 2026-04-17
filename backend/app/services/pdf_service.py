from pathlib import Path
import fitz  # PyMuPDF


def extract_text_from_pdf(file_path: str) -> str:
    pdf_path = Path(file_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    text_chunks = []

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text").strip()
            if page_text:
                text_chunks.append(f"--- Page {page_num} ---\n{page_text}")

    return "\n\n".join(text_chunks)