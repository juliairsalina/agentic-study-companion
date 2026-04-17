from pathlib import Path
from fastapi import UploadFile
import shutil


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(file: UploadFile) -> str:
    file_path = UPLOADS_DIR / file.filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(file_path)