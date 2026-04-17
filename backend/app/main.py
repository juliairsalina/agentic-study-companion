from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.upload import router as upload_router

app = FastAPI(
    title="Study Companion API",
    description="Backend API for the Agentic Study Companion hackathon project",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Study Companion API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(upload_router)